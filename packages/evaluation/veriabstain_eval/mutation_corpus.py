"""Deterministic G2 fixture authoring, independent of candidate verdict code.

Literal recipes/labels implement the independently reviewed, pre-frozen spec.
No historical fixtures/model data or candidate helpers are imported.
"""
import copy
import hashlib
import json
from pathlib import Path

from bnbagent.core.abis import load_abi
from eth_utils import keccak

SPEC_DIGEST='ab65a8334084bed433dad08b2a2dffe5eb1fa0e7ea295cc6b91865c60e9ac549'
TOKEN='0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565'
COMMERCE='0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE'
OWNER='0x'+'33'*20
SPENDER='0x'+'44'*20
OTHER='0x'+'11'*20
IMPLEMENTATION='0x55c3826B39a0F671B2C3E5D0F1372CaD0B911421'
SDK='260e16196931780d0370bd3a9d9b67ece744bb9d'
REVIEW='f6a3c4ff337158a8a66281c565f3f1562e1287b7'
CONTROLS=('matched','address_case','hash_hex_case','calldata_hex_case','json_layout',
          'historical_valid','freshness_boundary')
MUTATIONS=('wrong_chain','wrong_contract','function_mismatch','abi_mismatch','unreviewed_proxy',
    'runtime_mismatch','block_hash_mismatch','block_number_mismatch','stale_at_observation',
    'future_block','conflicting_evidence','rpc_unavailable','pruned_state','missing_return_data',
    'incorrect_assertion','numeric_scaling','unsupported_threshold','numeric_string',
    'invalid_return_bytes','calldata_argument_mismatch','historical_incorrect_assertion',
    'selector_mismatch','unfinalized','noncanonical')


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _word(value):
    return value.to_bytes(32,'big').hex()


def _address_word(value):
    return '0'*24+value[2:].lower()


def _golden_job():
    # Return tuple head is offset32; description at tuple offset11words=352.
    description=b'G2 synthetic job'
    tail=_word(len(description))+description.hex()+'00'*((-len(description))%32)
    head=[_word(4242),_address_word(OWNER),_address_word(SPENDER),_address_word(OTHER),
          _word(352),_word(10**18),_word(2000),_word(3),_address_word(OTHER),_word(1),'cd'*32]
    return '0x'+_word(32)+''.join(head)+tail


def _seed(predicate):
    job=predicate=='erc8183.job_status'
    target=COMMERCE if job else TOKEN
    function_name='getJob' if job else 'allowance'
    signature='getJob(uint256)' if job else 'allowance(address,address)'
    abi=load_abi('AgenticCommerce.json' if job else 'ERC20.json')
    function=next(entry for entry in abi if entry.get('type')=='function' and entry.get('name')==function_name)
    selector='0x'+keccak(text=signature)[:4].hex()
    calldata=selector+(_word(4242) if job else _address_word(OWNER)+_address_word(SPENDER))
    claim={'predicate':predicate,'chain_id':97,'target':target,
           'arguments':{'job_id':4242} if job else {'owner':OWNER,'spender':SPENDER},
           'block_number':40,'block_hash':'0x'+'ab'*32,'value':'COMPLETED' if job else 100}
    return {'kind':'veriabstain.evidence_envelope','envelope_version':1,'claim':claim,
        'observation':{'observed_at':1000,'block_timestamp':990,'max_block_age_seconds':120,
            'max_observation_age_seconds':300,'finalized':True,'canonical':True,'abi_supported':True,
            'error':'NONE','conflicting':False,'assurance':'SIMULATED_READ','source_id':'g2-synthetic-v1',
            'historical_state_capability':'AVAILABLE'},
        'identity':{'chain_id':97,'target':target,
            'target_code_hash':('0x1f1858db4825be798342d4c094630bf5ddc685bd802a083d8d88f15a6cdb2a89' if job
                                else '0xae12b1d61f7ed4febf649ccf319cb49a0e921cca3739dcb01b47d316049d46ff'),
            'review_source_revision':REVIEW,'pinset_id':'chain97-reviewed-20261120-v1',
            'proxy_implementation':IMPLEMENTATION if job else None,
            'implementation_code_hash':'0xb42935ea4e89b470ea5049cf66d7f1003a5c8d452aef72d78c666577e828380b' if job else None},
        'decoding':{'function_signature':signature,'selector':selector,
            'abi_sha256':hashlib.sha256(_json(function).encode()).hexdigest(),
            'codec':'web3-eth-abi-canonical-v1','sdk_revision':SDK,'calldata':calldata,
            'return_data':_golden_job() if job else '0x'+_word(100)},
        'reproduction':{'rpc_method':'eth_call','block_reference':'NUMBER_AND_HASH_PINNED',
            'chain_id':97,'target':target,'block_number':40,'block_hash':claim['block_hash'],'calldata':calldata}}


def _uppercase(value):
    return '0x'+value[2:].upper()


def _reverse(value):
    if isinstance(value,dict):
        return {key:_reverse(content) for key,content in reversed(list(value.items()))}
    return value


def _recipe(seed, category):
    package=copy.deepcopy(seed);now=1000
    claim,obs,identity,decoding,reproduction=(package[k] for k in ('claim','observation','identity','decoding','reproduction'))
    job=claim['predicate']=='erc8183.job_status'
    if category=='address_case':
        for item in (claim,identity,reproduction):item['target']=_uppercase(item['target'])
        for key,value in claim['arguments'].items():
            if isinstance(value,str):claim['arguments'][key]=_uppercase(value)
        if identity['proxy_implementation']:identity['proxy_implementation']=_uppercase(identity['proxy_implementation'])
    elif category=='hash_hex_case':
        for item in (claim,reproduction):item['block_hash']=_uppercase(item['block_hash'])
        identity['target_code_hash']=_uppercase(identity['target_code_hash'])
        if identity['implementation_code_hash']:identity['implementation_code_hash']=_uppercase(identity['implementation_code_hash'])
    elif category=='calldata_hex_case':
        for key in ('calldata','return_data','selector'):decoding[key]=_uppercase(decoding[key])
        reproduction['calldata']=decoding['calldata']
    elif category in ('historical_valid','historical_incorrect_assertion'):now=2000
    elif category=='freshness_boundary':obs['block_timestamp']=880
    elif category=='wrong_chain':claim['chain_id']=56
    elif category=='wrong_contract':claim['target']=OTHER
    elif category=='function_mismatch':decoding['function_signature']='balanceOf(address)'
    elif category=='abi_mismatch':decoding['abi_sha256']='0'*64
    elif category=='unreviewed_proxy':identity['proxy_implementation']=OTHER
    elif category=='runtime_mismatch':identity['target_code_hash']='0x'+'0'*64
    elif category=='block_hash_mismatch':reproduction['block_hash']='0x'+'cd'*32
    elif category=='block_number_mismatch':reproduction['block_number']=41
    elif category=='stale_at_observation':obs['block_timestamp']=879
    elif category=='future_block':obs['block_timestamp']=1001
    elif category=='conflicting_evidence':obs['conflicting']=True
    elif category in ('rpc_unavailable','pruned_state'):
        obs['error']='PRUNED_STATE' if category=='pruned_state' else 'RPC_UNAVAILABLE'
        obs['historical_state_capability']='PRUNED' if category=='pruned_state' else 'UNKNOWN'
        decoding['return_data']='0x'
    elif category=='missing_return_data':decoding['return_data']='0x'
    elif category=='numeric_scaling':claim['value']=100*10**18
    elif category=='unsupported_threshold':claim.update({'threshold':100,'operator':'gte'})
    elif category=='numeric_string':claim['value']='3' if job else '100'
    elif category=='invalid_return_bytes':decoding['return_data']='0x01'
    elif category=='calldata_argument_mismatch':
        decoding['calldata']=decoding['calldata'][:-64]+_word(9)
        reproduction['calldata']=decoding['calldata']
    elif category=='selector_mismatch':decoding['selector']='0x00000000'
    elif category=='unfinalized':obs['finalized']=False
    elif category=='noncanonical':obs['canonical']=False
    if category in ('incorrect_assertion','historical_incorrect_assertion'):
        claim['value']='FUNDED' if job else 101
    raw=json.dumps(_reverse(package),indent=3) if category=='json_layout' else _json(package)
    return raw,now


def _labels(category,predicate):
    # Literal independent oracle from frozen spec table; not candidate output.
    if category in CONTROLS:
        snapshot='VALID_AT_SNAPSHOT';temporal='REVALIDATION_REQUIRED' if category=='historical_valid' else 'CURRENT'
    elif category in ('incorrect_assertion','historical_incorrect_assertion') or (
            category=='numeric_scaling' and predicate=='erc20.allowance'):
        snapshot='INVALID_AT_SNAPSHOT';temporal='REVALIDATION_REQUIRED' if category=='historical_incorrect_assertion' else 'CURRENT'
    else:
        snapshot='UNSUPPORTED_OR_INCONCLUSIVE'
        temporal='CURRENT' if category in ('missing_return_data','invalid_return_bytes','calldata_argument_mismatch') else 'UNKNOWN'
    return {'snapshot_status':snapshot,'temporal_status':temporal,'authorization_status':'NOT_PROVIDED',
            'current_use_allowed':False,'execution_authorized':False}


def build_corpus():
    root=Path(__file__).resolve().parents[3]
    if hashlib.sha256((root/'docs/EVIDENCELAB_G2_SPEC.md').read_bytes()).hexdigest()!=SPEC_DIGEST:
        raise ValueError('Frozen specification changed; use a reviewed new version')
    cases=[]
    for predicate in ('erc20.allowance','erc8183.job_status'):
        seed=_seed(predicate)
        for category in (*CONTROLS,*MUTATIONS):
            raw,now=_recipe(seed,category)
            cases.append({'case_id':predicate+'/'+category,'predicate':predicate,'category':category,
                'control':category in CONTROLS,'rationale':'Frozen G2 spec v1.0 recipe '+category+
                    ': '+('valid representation/snapshot control' if category in CONTROLS else
                           'independently specified corruption or unsupported semantic case'),
                'now':now,'input_json':raw,'expected':_labels(category,predicate)})
    return {'corpus_kind':'veriabstain.evidencelab_mutations','corpus_version':'1.0',
            'spec_sha256':SPEC_DIGEST,'assurance':'SIMULATED_READ','cases':sorted(cases,key=lambda c:c['case_id'])}
