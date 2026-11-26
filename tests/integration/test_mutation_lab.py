"""G2 synthetic corpus conformance, not a G3 differential/value evaluation."""
import ast
import copy
import hashlib
import json
import re

import pytest
from eth_utils import keccak

from veriabstain_eval.mutation_manifest import (
    load_corpus,freeze_corpus,validate_manifest,DIRECTORY,SPEC,ROOT,CONTROLS,MUTATIONS,
)
from veriabstain_eval.mutation_corpus import build_corpus
from veriabstain_eval.evidence_envelope import assess_envelope
from veriabstain_eval.runner import offline
from veriabstain_eval.workers import strict_json

CORPUS,CHECKSUM=load_corpus()


def test_coverage_pairing_and_regeneration_are_exact():
    assert len(CORPUS['cases'])==62
    assert sum(case['control'] for case in CORPUS['cases'])==14
    assert len(CONTROLS)==7 and len(MUTATIONS)==24
    assert build_corpus()==CORPUS
    assert CHECKSUM==hashlib.sha256((DIRECTORY/'corpus.json').read_bytes()).hexdigest()


def test_golden_labels_match_frozen_spec_table_not_candidate():
    table={}
    for line in SPEC.read_text().splitlines():
        if not line.startswith('| '):continue
        cells=[cell.strip() for cell in line.split('|')]
        if re.fullmatch(r'[a-z_]+',cells[1]) and cells[-3] in ('V/C','V/R','I/C','I/R','U/C','U/Q'):
            table[cells[1]]=(cells[-3],cells[-2])
    assert set(table)==CONTROLS|MUTATIONS
    statuses={'V':'VALID_AT_SNAPSHOT','I':'INVALID_AT_SNAPSHOT','U':'UNSUPPORTED_OR_INCONCLUSIVE'}
    times={'C':'CURRENT','R':'REVALIDATION_REQUIRED','Q':'UNKNOWN'}
    for case in CORPUS['cases']:
        expected_code=table[case['category']][0 if case['predicate']=='erc20.allowance' else 1]
        snapshot,temporal=expected_code.split('/')
        assert case['expected']=={'snapshot_status':statuses[snapshot],'temporal_status':times[temporal],
            'authorization_status':'NOT_PROVIDED','current_use_allowed':False,'execution_authorized':False}


def test_generator_has_no_candidate_or_historical_oracle_imports():
    path=ROOT/'packages/evaluation/veriabstain_eval/mutation_corpus.py'
    tree=ast.parse(path.read_text())
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):imports.extend(name.name for name in node.names)
        elif isinstance(node,ast.ImportFrom):imports.append(node.module or '')
    assert all(name.split('.')[0] in {'copy','hashlib','json','pathlib','bnbagent','eth_utils'} for name in imports)
    source=path.read_text()
    assert 'assess_envelope(' not in source and 'expected_contract_identity(' not in source
    assert 'responses.jsonl' not in source and 'fixtures/g1a' not in source


@pytest.mark.parametrize('predicate',['erc20.allowance','erc8183.job_status'])
def test_independent_golden_bytes_and_call_words(predicate):
    case=next(c for c in CORPUS['cases'] if c['predicate']==predicate and c['category']=='matched')
    value=strict_json(case['input_json']);raw=bytes.fromhex(value['decoding']['return_data'][2:])
    calldata=bytes.fromhex(value['decoding']['calldata'][2:])
    if predicate=='erc20.allowance':
        assert calldata[:4].hex()=='dd62ed3e'
        assert calldata[4:]==bytes(12)+bytes.fromhex('33'*20)+bytes(12)+bytes.fromhex('44'*20)
        assert raw==bytes(31)+b'\x64' and value['claim']['value']==100
    else:
        assert calldata[:4]==keccak(text='getJob(uint256)')[:4]
        assert len(calldata)==36 and int.from_bytes(calldata[4:],'big')==4242
        assert int.from_bytes(raw[:32],'big')==32
        word=lambda i:int.from_bytes(raw[32+i*32:64+i*32],'big')
        assert (word(0),word(4),word(5),word(6),word(7),word(9))==(4242,352,10**18,2000,3,1)
        start=32+352;size=int.from_bytes(raw[start:start+32],'big')
        assert raw[start+32:start+32+size]==b'G2 synthetic job'
        assert value['claim']['value']=='COMPLETED'


@pytest.mark.parametrize('case',CORPUS['cases'],ids=lambda case:case['case_id'])
def test_frozen_case(case):
    with offline():
        result=assess_envelope(strict_json(case['input_json']),now=case['now']).model_dump()
    actual={field:result[field] for field in case['expected']}
    assert actual==case['expected'],json.dumps({'id':case['case_id'],'expected':case['expected'],'actual':actual})
    assert result['authenticity']=='NOT_ESTABLISHED'
    assert result['assurance'] in ('SIMULATED_READ',None)


def test_freeze_refuses_existing_files(tmp_path):
    freeze_corpus(CORPUS,tmp_path)
    before=(tmp_path/'corpus.json').read_bytes()
    with pytest.raises(ValueError,match='exists'):freeze_corpus(CORPUS,tmp_path)
    assert (tmp_path/'corpus.json').read_bytes()==before


def test_changed_corpus_or_spec_fails_closed(tmp_path):
    freeze_corpus(CORPUS,tmp_path)
    path=tmp_path/'corpus.json';path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='checksum'):load_corpus(tmp_path)
    path.write_bytes((DIRECTORY/'corpus.json').read_bytes())
    other_spec=tmp_path/'other-spec.md';other_spec.write_text('modified spec')
    with pytest.raises(ValueError,match='specification'):load_corpus(tmp_path,spec=other_spec)


@pytest.mark.parametrize('change',['extra_top','extra_case','count','duplicate','category','control','order','unsafe_expected'])
def test_malformed_manifest_rejected(change):
    value=copy.deepcopy(CORPUS)
    if change=='extra_top':value['extra']=True
    elif change=='extra_case':value['cases'][0]['extra']=True
    elif change=='count':value['cases'].pop()
    elif change=='duplicate':value['cases'][1]=value['cases'][0]
    elif change=='category':value['cases'][0]['category']='unknown'
    elif change=='control':value['cases'][0]['control']=not value['cases'][0]['control']
    elif change=='order':value['cases'].reverse()
    elif change=='unsafe_expected':value['cases'][0]['expected']['execution_authorized']=True
    with pytest.raises(ValueError):validate_manifest(value,spec_digest=CORPUS['spec_sha256'])
