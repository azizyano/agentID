"""Frozen G3 offline evaluation harness; not a G4 user workflow or paid runner."""
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

from .deterministic_baseline import assess_baseline
from .evidence_envelope import assess_envelope
from .mutation_manifest import ROOT,load_corpus
from .runner import offline
from .workers import canonical,strict_json

PROTOCOL_SHA='973dfb8f12740fc734bbf49af701562410bc39822d0cd19bcdeb5b494e2c03ec'
CORPUS_SHA='dbf197d8c86274c3d0855db0ffa9c766e448292aea72b4c0763afc44d144f6c3'
SEED=20261121
WARMUPS=2
ROUNDS=20
OUTCOMES=('snapshot_status','temporal_status','authorization_status','current_use_allowed','execution_authorized')


def _hash(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


def _write(path,value):
    with path.open('x',encoding='utf-8') as target:
        json.dump(value,target,indent=2,allow_nan=False);target.write('\n')
        target.flush();os.fsync(target.fileno())


def _invoke(function,package,now):
    # Identical copying/digest/normalization costs excluded from both timers.
    data=copy.deepcopy(package);before=_hash(data)
    start=time.perf_counter_ns()
    try:
        raw=function(data,now=now)
    except Exception as error:
        elapsed=time.perf_counter_ns()-start
        return {'reason':'ASSESSMENT_EXCEPTION','error_type':type(error).__name__},elapsed,False
    elapsed=time.perf_counter_ns()-start
    unchanged=before==_hash(data)
    result=raw if isinstance(raw,dict) else raw.model_dump()
    return result,elapsed,unchanged


def stats(samples):
    ordered=sorted(samples)
    return {'samples':len(ordered),'median_us':statistics.median(ordered)/1000,
            'p95_us':ordered[math.ceil(.95*len(ordered))-1]/1000}


def advantage_gates(wins,regressions,candidate,ratios):
    safe=(candidate['false_acceptances']==0 and candidate['execution_grants']==0
          and candidate['control_outcome_errors']==0 and candidate['unauthorized_current_use']==0)
    return {'correctness_advantage':len(wins)-len(regressions)>=2 and safe,
            'runtime_advantage':all(value<=.8 for value in ratios.values()) and safe and not regressions}


def same_outcomes(actual,expected):
    return (set(actual)==set(expected) and all(type(actual[k]) is type(expected[k])
                                              and actual[k]==expected[k] for k in expected))


def run_differential(directory):
    directory=Path(directory)
    protocol=ROOT/'docs/EVIDENCELAB_G3_PROTOCOL.md'
    if hashlib.sha256(protocol.read_bytes()).hexdigest()!=PROTOCOL_SHA:raise ValueError('Protocol changed')
    corpus,checksum=load_corpus()
    if checksum!=CORPUS_SHA:raise ValueError('Corpus changed')
    cases=corpus['cases'];packages={c['case_id']:strict_json(c['input_json']) for c in cases}
    source_files=('evidence_envelope.py','deterministic_baseline.py','differential.py',
                  'chain_evidence.py','testnet_deployment.py','deliverables.py','workers.py',
                  'dataset.py','mutation_manifest.py')
    code_hashes={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in source_files}
    directory.mkdir(parents=True,exist_ok=False)
    _write(directory/'run-config.json',{'status':'CONFIG_RECORDED_BEFORE_EXECUTION','protocol_sha256':PROTOCOL_SHA,
        'corpus_sha256':checksum,'code_sha256':code_hashes,'seed':SEED,'warmup_rounds':WARMUPS,'measured_rounds':ROUNDS,
        'timing':'assessment only; deep copies/content digests/return normalization excluded',
        'baseline_cache':'lru_cache immutable ABI metadata maxsize2; warm before timing',
        'candidate_cache':'existing G1 implementation unchanged; uses upstream ABI loader',
        'warmup_note':'One untimed correctness pass per system precedes two complete warm-up rounds',
        'source_hash_limit':'Listed local sources and package versions; not full transitive source attestation',
        'python':sys.version.split()[0],'platform':platform.system()+' '+platform.machine(),
        'assurance':corpus['assurance'],
        'package_versions':{name:importlib.metadata.version(name) for name in ('pydantic','web3','eth-abi','bnbagent')},
        'effort':'NOT_MEASURED: no matched independent participant/time logs',
        'network_calls':0,'model_calls':0,'transactions':0})
    results=[];timings=[];functions={'baseline':assess_baseline,'candidate':assess_envelope}
    try:
        with offline():
            for case in cases:
                row={'case_id':case['case_id'],'control':case['control'],'expected':case['expected'],
                     'assurance':corpus['assurance']}
                for name,function in functions.items():
                    output,_,unchanged=_invoke(function,packages[case['case_id']],case['now'])
                    actual={field:output.get(field) for field in OUTCOMES}
                    row[name]={'actual':actual,'correct':same_outcomes(actual,case['expected']) and unchanged,
                               'input_unchanged':unchanged,'reason':output.get('reason'),
                               'error_type':output.get('error_type'),
                               'mismatched_fields':[field for field in OUTCOMES if type(actual[field]) is not type(case['expected'][field]) or actual[field]!=case['expected'][field]]}
                results.append(row)
            rng=random.Random(SEED)
            for round_number in range(WARMUPS+ROUNDS):
                schedule=list(cases);rng.shuffle(schedule)
                for case in schedule:
                    names=list(functions)
                    if rng.getrandbits(1):names.reverse()
                    for order,name in enumerate(names):
                        output,elapsed,unchanged=_invoke(functions[name],packages[case['case_id']],case['now'])
                        actual={field:output.get(field) for field in OUTCOMES}
                        stable=same_outcomes(actual,next(r[name]['actual'] for r in results if r['case_id']==case['case_id']))
                        if not unchanged or not stable:raise ValueError('Input mutation or unstable outcome')
                        if round_number>=WARMUPS:
                            timings.append({'round':round_number-WARMUPS,'case_id':case['case_id'],
                                'predicate':case['predicate'],'system':name,'order':order,'nanoseconds':elapsed})
    except Exception as error:
        _write(directory/'failed-run.json',{'status':'ERROR','error_type':type(error).__name__,
            'partial_case_results':results,'partial_timings':timings,'assurance':corpus['assurance']})
        raise
    systems={}
    for name in functions:
        confusion={}
        for row in results:
            pair=row['expected']['snapshot_status']+' -> '+str(row[name]['actual']['snapshot_status'])
            confusion[pair]=confusion.get(pair,0)+1
        systems[name]={'correct_cases':sum(row[name]['correct'] for row in results),
            'valid_control_rejections':sum(row['control'] and row[name]['actual']['snapshot_status']!='VALID_AT_SNAPSHOT' for row in results),
            'control_outcome_errors':sum(row['control'] and not row[name]['correct'] for row in results),
            'false_acceptances':sum(row['expected']['snapshot_status']!='VALID_AT_SNAPSHOT' and row[name]['actual']['snapshot_status']=='VALID_AT_SNAPSHOT' for row in results),
            'temporal_errors':sum(row[name]['actual']['temporal_status']!=row['expected']['temporal_status'] for row in results),
            'authorization_errors':sum(row[name]['actual']['authorization_status']!=row['expected']['authorization_status'] for row in results),
            'execution_grants':sum(row[name]['actual']['execution_authorized'] is not False for row in results),
            'unauthorized_current_use':sum(row['expected']['current_use_allowed'] is False and row[name]['actual']['current_use_allowed'] is not False for row in results),
            'snapshot_confusion':confusion,
            'timing':stats([t['nanoseconds'] for t in timings if t['system']==name]),
            'timing_by_predicate':{predicate:stats([t['nanoseconds'] for t in timings if t['system']==name and t['predicate']==predicate]) for predicate in ('erc20.allowance','erc8183.job_status')}}
    regressions=[row['case_id'] for row in results if row['baseline']['correct'] and not row['candidate']['correct']]
    wins=[row['case_id'] for row in results if row['candidate']['correct'] and not row['baseline']['correct']]
    ratios={metric:systems['candidate']['timing'][metric]/systems['baseline']['timing'][metric] for metric in ('median_us','p95_us')}
    gates=advantage_gates(wins,regressions,systems['candidate'],ratios)
    summary={'phase':'EvidenceLab_G3','cases':len(results),'known_set_not_blind':True,'systems':systems,
        'assurance':corpus['assurance'],
        'candidate_only_correct':wins,'baseline_only_correct':regressions,'timing_candidate_over_baseline':ratios,
        **gates,
        'integration_effort_advantage':'NOT_MEASURED','reviewer_effort_advantage':'NOT_MEASURED',
        'recommendation':'GO_FOR_OWNER_REVIEW' if gates['correctness_advantage'] or gates['runtime_advantage'] else 'NO_GO_FOR_STANDALONE_EXPANSION_ON_THIS_EVIDENCE',
        'network_calls':0,'model_calls':0,'transactions':0,
        'limitations':['Known synthetic corpus; no population generalization','No matched independent effort measurements',
                       'Provider transcripts not authenticated','No live RPC acquisition or G4workflow tested']}
    _write(directory/'case-results.json',results);_write(directory/'timings.json',timings)
    _write(directory/'summary.json',summary)
    return summary
