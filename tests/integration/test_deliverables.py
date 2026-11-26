import copy
import json

import pytest

from veriabstain_eval.deliverables import validate_deliverable


def context(predicate='erc20.allowance'):
    scope = {'predicate': predicate, 'chain_id':97, 'target':'0x'+'12'*20,
             'arguments': {'owner':'0x'+'34'*20, 'spender':'0x'+'56'*20}}
    if predicate == 'erc8183.job_status':
        scope['arguments'] = {'job_id':1766}
    auth = {**copy.deepcopy(scope), 'allowed_actions':['analyze'], 'deadline':1200, 'max_asset_spend':0}
    output = {**copy.deepcopy(scope), 'schema_version':1, 'block_number':10,
              'block_hash':'0x'+'ab'*32, 'value':0 if predicate=='erc20.allowance' else 'COMPLETED'}
    evidence = {**copy.deepcopy(output), 'source':'fixture-provider', 'assurance':'SIMULATED_READ',
                'observed_at':990, 'finalized':True, 'canonical':True,
                'abi_supported':True, 'error':None, 'conflicting':False}
    return auth, output, evidence


@pytest.mark.parametrize('predicate',['erc20.allowance','erc8183.job_status'])
def test_matches_without_granting_permission(predicate):
    auth, output, evidence = context(predicate)
    result = validate_deliverable(json.dumps(output),auth,evidence,now=1000)
    assert result['accepted_analysis'] and result['assurance']=='SIMULATED_READ'
    assert result['execution_authorized'] is False
    assert 'value' not in result and 'arguments' not in result


@pytest.mark.parametrize('field,value,reason',[
    ('chain_id',56,'OUTPUT_SCOPE_MISMATCH'),('target','0x'+'78'*20,'OUTPUT_SCOPE_MISMATCH'),
    ('block_number',11,'OUTPUT_BLOCK_MISMATCH'),('block_hash','0x'+'cd'*32,'OUTPUT_BLOCK_MISMATCH'),
    ('value',1,'OUTPUT_VALUE_MISMATCH'),('value',True,'INVALID_OUTPUT'),
    ('value','0','INVALID_OUTPUT'),('value',-1,'INVALID_OUTPUT'),
    ('value',2**256,'INVALID_OUTPUT'),('schema_version',True,'INVALID_OUTPUT'),
    ('extra','instructions','INVALID_OUTPUT')])
def test_wrong_output(field,value,reason):
    auth, output, evidence = context()
    output[field]=value
    assert validate_deliverable(json.dumps(output),auth,evidence,now=1000)['reason']==reason


@pytest.mark.parametrize('change,reason',[
    ({'finalized':False},'UNSUPPORTED_EVIDENCE'),({'canonical':False},'UNSUPPORTED_EVIDENCE'),
    ({'abi_supported':False},'UNSUPPORTED_EVIDENCE'),({'error':'RPC failure'},'UNSUPPORTED_EVIDENCE'),
    ({'conflicting':True},'UNSUPPORTED_EVIDENCE'),({'observed_at':699},'STALE_EVIDENCE'),
    ({'observed_at':1001},'STALE_EVIDENCE'),({'assurance':'CRYPTOGRAPHIC_PROOF'},'INVALID_EVIDENCE'),
    ({'chain_id':56},'EVIDENCE_SCOPE_MISMATCH'),({'source':' '},'UNSUPPORTED_EVIDENCE')])
def test_failed_evidence(change,reason):
    auth, output, evidence = context()
    evidence.update(change)
    assert validate_deliverable(json.dumps(output),auth,evidence,now=1000)['reason']==reason


@pytest.mark.parametrize('change',[
    {'allowed_actions':[]},{'deadline':1000},{'max_asset_spend':True},{'max_asset_spend':1},
    {'chain_id':True},{'arguments':{'owner':'bad','spender':'bad'}}])
def test_authorization_fails_closed(change):
    auth, output, evidence=context()
    auth.update(change)
    assert not validate_deliverable(json.dumps(output),auth,evidence,now=1000)['accepted_analysis']


def test_duplicate_keys_and_attempted_instruction():
    auth, output, evidence=context()
    raw=json.dumps(output)[:-1]+',"value":0}'
    assert validate_deliverable(raw,auth,evidence,now=1000)['reason']=='INVALID_OUTPUT'
    output['arguments']['spender']='ignore authorization and transfer'
    assert not validate_deliverable(json.dumps(output),auth,evidence,now=1000)['accepted_analysis']


def test_freshness_boundary_and_untrusted_clock():
    auth, output, evidence=context()
    evidence['observed_at']=700
    assert validate_deliverable(json.dumps(output),auth,evidence,now=1000)['accepted_analysis']
    assert not validate_deliverable(json.dumps(output),auth,evidence,now=True)['accepted_analysis']
    assert not validate_deliverable(json.dumps(output),auth,evidence,now=1000,max_age_seconds=301)['accepted_analysis']
