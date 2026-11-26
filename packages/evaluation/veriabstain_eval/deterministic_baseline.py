"""Independent plain-data G3 baseline. No candidate/legacy verdict imports.

Consumes the same recorded JSON facts; it does not fetch or authenticate state.
Reviewed definitions are duplicated explicitly, with upstream ABI as common fact.
"""
import hashlib
import json
import re
from functools import lru_cache

from bnbagent.core.abis import load_abi
from eth_abi import decode,encode
from eth_utils import keccak
from eth_utils.abi import collapse_if_tuple

ADDR=r'0x[0-9a-fA-F]{40}'
HASH=r'0x[0-9a-fA-F]{64}'
STATUSES=('OPEN','FUNDED','SUBMITTED','COMPLETED','REJECTED','EXPIRED')
PREDICATES=('erc20.allowance','erc8183.job_status')
TOKEN='0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565'
COMMERCE='0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE'
FIELDS={
    'claim':{'predicate','chain_id','target','arguments','block_number','block_hash','value'},
    'observation':{'observed_at','block_timestamp','max_block_age_seconds','max_observation_age_seconds',
                   'finalized','canonical','abi_supported','error','conflicting','assurance','source_id',
                   'historical_state_capability'},
    'identity':{'chain_id','target','target_code_hash','review_source_revision','pinset_id',
                'proxy_implementation','implementation_code_hash'},
    'decoding':{'function_signature','selector','abi_sha256','codec','sdk_revision','calldata','return_data'},
    'reproduction':{'rpc_method','block_reference','chain_id','target','block_number','block_hash','calldata'},
}


def _matches(pattern,value):
    return type(value) is str and re.fullmatch(pattern,value) is not None


def _uint(value):
    return type(value) is int and 0<=value<2**256


def _bytes(value):
    return type(value) is str and len(value)<=131074 and _matches(r'0x(?:[0-9a-fA-F]{2})*',value)


def _bounded(value,depth=0,budget=None):
    if budget is None:budget=[4096]
    budget[0]-=1
    if depth>16 or budget[0]<0:raise ValueError('Unsupported size')
    if type(value) is dict:
        if any(type(k) is not str for k in value):raise ValueError('Unsupported key')
        for item in value.values():_bounded(item,depth+1,budget)
    elif type(value) is list:
        for item in value:_bounded(item,depth+1,budget)
    elif type(value) not in (str,int,bool,type(None)) or (type(value) is str and len(value)>131074):
        raise ValueError('Unsupported primitive')


def _scope(value):
    if (value['predicate'] not in PREDICATES or type(value['chain_id']) is not int
            or value['chain_id']<=0 or not _matches(ADDR,value['target']) or type(value['arguments']) is not dict):
        return False
    args=value['arguments']
    if value['predicate']=='erc20.allowance':
        return set(args)=={'owner','spender'} and all(_matches(ADDR,v) for v in args.values())
    return set(args)=={'job_id'} and _uint(args['job_id']) and args['job_id']>0


def _shape(package):
    _bounded(package)
    if (type(package) is not dict or set(package)!={'kind','envelope_version',*FIELDS}
            or package['kind']!='veriabstain.evidence_envelope'
            or type(package['envelope_version']) is not int or package['envelope_version']!=1):return False
    if any(type(package[k]) is not dict or set(package[k])!=fields for k,fields in FIELDS.items()):return False
    c,o,i,d,r=(package[k] for k in FIELDS)
    if not _scope(c) or not _uint(c['block_number']) or not _matches(HASH,c['block_hash']):return False
    if c['predicate']=='erc20.allowance':
        if not _uint(c['value']):return False
    elif type(c['value']) is not str or c['value'] not in STATUSES:return False
    if (not _uint(o['observed_at']) or not _uint(o['block_timestamp'])
            or type(o['max_block_age_seconds']) is not int or not 0<=o['max_block_age_seconds']<=120
            or type(o['max_observation_age_seconds']) is not int or not 0<=o['max_observation_age_seconds']<=300
            or any(type(o[k]) is not bool for k in ('finalized','canonical','abi_supported','conflicting'))
            or o['error'] not in ('NONE','RPC_UNAVAILABLE','MISSING_STATE','PRUNED_STATE','DECODE_FAILED')
            or o['historical_state_capability'] not in ('AVAILABLE','PRUNED','MISSING_STATE','UNSUPPORTED','UNKNOWN')
            or o['assurance'] not in ('RPC_FINALIZED_READ','SIMULATED_READ')
            or not _matches(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',o['source_id'])):return False
    if (type(i['chain_id']) is not int or i['chain_id']<=0 or not _matches(ADDR,i['target'])
            or not _matches(HASH,i['target_code_hash']) or not _matches(r'[0-9a-f]{40}',i['review_source_revision'])
            or i['pinset_id']!='chain97-reviewed-20261120-v1'
            or (i['proxy_implementation'] is not None and not _matches(ADDR,i['proxy_implementation']))
            or (i['implementation_code_hash'] is not None and not _matches(HASH,i['implementation_code_hash']))):return False
    if (type(d['function_signature']) is not str or not 1<=len(d['function_signature'])<=128
            or not _matches(r'0x[0-9a-fA-F]{8}',d['selector']) or not _matches(r'[0-9a-f]{64}',d['abi_sha256'])
            or d['codec']!='web3-eth-abi-canonical-v1' or not _matches(r'[0-9a-f]{40}',d['sdk_revision'])
            or not _bytes(d['calldata']) or not _bytes(d['return_data'])):return False
    return (r['rpc_method']=='eth_call' and r['block_reference']=='NUMBER_AND_HASH_PINNED'
            and type(r['chain_id']) is int and r['chain_id']>0 and _matches(ADDR,r['target'])
            and _uint(r['block_number']) and _matches(HASH,r['block_hash']) and _bytes(r['calldata']))


@lru_cache(maxsize=2)
def _abi(predicate):
    job=predicate=='erc8183.job_status';name='getJob' if job else 'allowance'
    entries=[f for f in load_abi('AgenticCommerce.json' if job else 'ERC20.json')
             if f.get('type')=='function' and f.get('name')==name]
    if len(entries)!=1:raise ValueError('Unsupported ABI')
    f=entries[0];inputs=tuple(collapse_if_tuple(item) for item in f['inputs'])
    outputs=tuple(collapse_if_tuple(item) for item in f['outputs'])
    signature=name+'('+','.join(inputs)+')'
    canonical=json.dumps(f,sort_keys=True,separators=(',',':'),allow_nan=False)
    return inputs,outputs,signature,keccak(text=signature)[:4],hashlib.sha256(canonical.encode()).hexdigest()


def _authorization(authorization,claim,now):
    if authorization is None:return 'NOT_PROVIDED'
    try:
        _bounded(authorization)
        if (type(authorization) is not dict or set(authorization)!={'predicate','chain_id','target','arguments',
                'allowed_actions','deadline','max_asset_spend'} or not _scope(authorization)
                or type(authorization['deadline']) is not int or authorization['deadline']<0
                or now>=authorization['deadline'] or type(authorization['max_asset_spend']) is not int
                or authorization['max_asset_spend']!=0 or type(authorization['allowed_actions']) is not list
                or not all(type(v) is str for v in authorization['allowed_actions'])
                or 'analyze' not in authorization['allowed_actions']):return 'BLOCKED'
        same=(authorization['predicate']==claim['predicate'] and authorization['chain_id']==claim['chain_id']
              and authorization['target'].lower()==claim['target'].lower()
              and {k:v.lower() if type(v) is str else v for k,v in authorization['arguments'].items()}
                  =={k:v.lower() if type(v) is str else v for k,v in claim['arguments'].items()})
        return 'CURRENTLY_AUTHORIZED' if same else 'BLOCKED'
    except Exception:return 'BLOCKED'


def assess_baseline(package,*,now,authorization=None):
    snapshot='UNSUPPORTED_OR_INCONCLUSIVE';temporal='UNKNOWN';auth='NOT_PROVIDED'
    def result(reason):
        return {'snapshot_status':snapshot,'temporal_status':temporal,'authorization_status':auth,
                'current_use_allowed':snapshot=='VALID_AT_SNAPSHOT' and temporal=='CURRENT' and auth=='CURRENTLY_AUTHORIZED',
                'execution_authorized':False,'reason':reason,'authenticity':'NOT_ESTABLISHED'}
    try:
        if type(now) is not int or now<0 or not _shape(package):
            auth='BLOCKED' if authorization is not None else auth
            return result('UNSUPPORTED_INPUT')
        c,o,i,d,r=(package[k] for k in FIELDS)
        auth=_authorization(authorization,c,now)
        job=c['predicate']=='erc8183.job_status'
        expected_target=COMMERCE if job else TOKEN
        expected_code=('0x1f1858db4825be798342d4c094630bf5ddc685bd802a083d8d88f15a6cdb2a89' if job
                       else '0xae12b1d61f7ed4febf649ccf319cb49a0e921cca3739dcb01b47d316049d46ff')
        if (c['chain_id']!=97 or i['chain_id']!=97 or c['target'].lower()!=expected_target.lower()
                or i['target'].lower()!=expected_target.lower() or i['target_code_hash'].lower()!=expected_code
                or i['review_source_revision']!='f6a3c4ff337158a8a66281c565f3f1562e1287b7'):
            return result('UNREVIEWED_IDENTITY')
        if job:
            if (i['proxy_implementation'] is None or i['proxy_implementation'].lower()!='0x55c3826b39a0f671b2c3e5d0f1372cad0b911421'
                    or i['implementation_code_hash'] is None or i['implementation_code_hash'].lower()!=
                    '0xb42935ea4e89b470ea5049cf66d7f1003a5c8d452aef72d78c666577e828380b'):return result('UNREVIEWED_PROXY')
        elif i['proxy_implementation'] is not None or i['implementation_code_hash'] is not None:return result('UNREVIEWED_PROXY')
        inputs,outputs,signature,selector,abi_digest=_abi(c['predicate'])
        if (d['function_signature']!=signature or d['selector'].lower()!='0x'+selector.hex()
                or d['abi_sha256']!=abi_digest or d['sdk_revision']!='260e16196931780d0370bd3a9d9b67ece744bb9d'):
            return result('UNSUPPORTED_DECODING')
        if (r['chain_id']!=c['chain_id'] or r['target'].lower()!=c['target'].lower()
                or r['block_number']!=c['block_number'] or r['block_hash'].lower()!=c['block_hash'].lower()
                or r['calldata'].lower()!=d['calldata'].lower()):return result('CONTEXT_MISMATCH')
        if (not o['finalized'] or not o['canonical'] or not o['abi_supported'] or o['conflicting']
                or o['error']!='NONE' or o['historical_state_capability']!='AVAILABLE'):
            return result('INCOMPLETE_OBSERVATION')
        if not 0<=o['observed_at']-o['block_timestamp']<=o['max_block_age_seconds'] or now<o['observed_at']:
            return result('UNSUPPORTED_TIME')
        temporal='CURRENT' if (now-o['observed_at']<=o['max_observation_age_seconds']
                               and now-o['block_timestamp']<=o['max_block_age_seconds']) else 'REVALIDATION_REQUIRED'
        if d['calldata']=='0x' or d['return_data']=='0x':return result('MISSING_TRANSCRIPT')
        args=[c['arguments']['job_id']] if job else [c['arguments']['owner'],c['arguments']['spender']]
        if bytes.fromhex(d['calldata'][2:])!=selector+encode(inputs,args):return result('CALL_MISMATCH')
        raw=bytes.fromhex(d['return_data'][2:]);decoded=decode(outputs,raw)
        if encode(outputs,decoded)!=raw:return result('NONCANONICAL_RETURN')
        value=decoded[0]
        if job:
            if len(value)!=11 or value[0]!=c['arguments']['job_id'] or not 0<=value[7]<len(STATUSES):
                return result('UNSUPPORTED_JOB')
            value=STATUSES[value[7]]
        snapshot='VALID_AT_SNAPSHOT' if type(value) is type(c['value']) and value==c['value'] else 'INVALID_AT_SNAPSHOT'
        return result('COMPARED_RAW_VALUE')
    except Exception:
        return result('UNSUPPORTED_INPUT_OR_TRANSCRIPT')
