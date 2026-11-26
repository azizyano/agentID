"""Load/freeze only the separate G2 synthetic corpus; no candidate verdict oracle."""
import hashlib
import re
from pathlib import Path

from .dataset import canonical
from .workers import strict_json

ROOT=Path(__file__).resolve().parents[3]
DIRECTORY=ROOT/'fixtures/evidencelab/g2-v1'
SPEC=ROOT/'docs/EVIDENCELAB_G2_SPEC.md'
CONTROLS=frozenset({'matched','address_case','hash_hex_case','calldata_hex_case','json_layout',
                    'historical_valid','freshness_boundary'})
MUTATIONS=frozenset({'wrong_chain','wrong_contract','function_mismatch','abi_mismatch',
    'unreviewed_proxy','runtime_mismatch','block_hash_mismatch','block_number_mismatch',
    'stale_at_observation','future_block','conflicting_evidence','rpc_unavailable','pruned_state',
    'missing_return_data','incorrect_assertion','numeric_scaling','unsupported_threshold',
    'numeric_string','invalid_return_bytes','calldata_argument_mismatch','historical_incorrect_assertion',
    'selector_mismatch','unfinalized','noncanonical'})
PREDICATES=('erc20.allowance','erc8183.job_status')


def validate_manifest(corpus, *, spec_digest):
    if (not isinstance(corpus,dict)
            or set(corpus)!={'corpus_kind','corpus_version','spec_sha256','assurance','cases'}
            or corpus.get('corpus_kind')!='veriabstain.evidencelab_mutations'
            or corpus.get('corpus_version')!='1.0'
            or corpus.get('spec_sha256')!=spec_digest
            or corpus.get('assurance')!='SIMULATED_READ'
            or not isinstance(corpus.get('cases'),list) or len(corpus['cases'])!=62):
        raise ValueError('Unsupported corpus or specification mismatch')
    ids=set()
    for case in corpus['cases']:
        if (not isinstance(case,dict) or not isinstance(case.get('case_id'),str)
                or set(case)!={'case_id','predicate','category','control','rationale','now','input_json','expected'}
                or not re.fullmatch(r'[a-z0-9_.:/-]{1,160}',case['case_id'])
                or case['case_id'] in ids or type(case.get('control')) is not bool
                or case.get('predicate') not in ('erc20.allowance','erc8183.job_status')
                or type(case.get('now')) is not int or case['now']<0
                or not isinstance(case.get('input_json'),str)
                or len(case['input_json'].encode())>65_536
                or not isinstance(case.get('rationale'),str) or not case['rationale'].strip()
                or len(case['rationale'])>1024 or not isinstance(case.get('category'),str)
                or case['category'] not in CONTROLS|MUTATIONS
                or case['control']!=(case['category'] in CONTROLS)
                or case['case_id']!=case['predicate']+'/'+case['category']):
            raise ValueError('Invalid corpus case')
        expected=case.get('expected')
        if (not isinstance(expected,dict)
                or set(expected)!={'snapshot_status','temporal_status','authorization_status',
                                   'current_use_allowed','execution_authorized'}
                or expected['snapshot_status'] not in ('VALID_AT_SNAPSHOT','INVALID_AT_SNAPSHOT',
                                                      'UNSUPPORTED_OR_INCONCLUSIVE')
                or expected['temporal_status'] not in ('CURRENT','REVALIDATION_REQUIRED','UNKNOWN')
                or expected['authorization_status']!='NOT_PROVIDED'
                or expected['current_use_allowed'] is not False or expected['execution_authorized'] is not False):
            raise ValueError('Unsupported independently specified outcome')
        ids.add(case['case_id'])
    if ids!={predicate+'/'+category for predicate in PREDICATES for category in CONTROLS|MUTATIONS}:
        raise ValueError('Corpus coverage or pairing differs from frozen specification')
    if [case['case_id'] for case in corpus['cases']]!=sorted(ids):
        raise ValueError('Corpus order differs from frozen specification')
    return corpus


def load_corpus(directory=DIRECTORY, *, spec=SPEC):
    directory=Path(directory)
    with (directory/'corpus.json').open('rb') as source:
        raw=source.read(4_194_305)
    if len(raw)>4_194_304:
        raise ValueError('Corpus exceeds limit')
    checksum=(directory/'corpus.sha256').read_text(encoding='ascii').strip()
    actual=hashlib.sha256(raw).hexdigest()
    if not re.fullmatch(r'[a-f0-9]{64}',checksum) or actual!=checksum:
        raise ValueError('Frozen corpus checksum mismatch')
    spec_digest=hashlib.sha256(Path(spec).read_bytes()).hexdigest()
    return validate_manifest(strict_json(raw.decode('utf-8')),spec_digest=spec_digest),actual


def freeze_corpus(corpus, directory=DIRECTORY, *, spec=SPEC):
    """Exclusive initial creation, never regenerate an existing scored corpus."""
    spec_digest=hashlib.sha256(Path(spec).read_bytes()).hexdigest()
    validate_manifest(corpus,spec_digest=spec_digest)
    raw=(canonical(corpus)+'\n').encode('utf-8')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    if (directory/'corpus.json').exists() or (directory/'corpus.sha256').exists():
        raise ValueError('Frozen corpus exists; use a reviewed new version instead')
    with (directory/'corpus.json').open('xb') as target:
        target.write(raw)
    checksum=hashlib.sha256(raw).hexdigest()
    with (directory/'corpus.sha256').open('x',encoding='ascii') as target:
        target.write(checksum+'\n')
    return checksum
