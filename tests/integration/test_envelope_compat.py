import copy
import json

import pytest

from veriabstain_eval.envelope_compat import import_legacy,assess_legacy_import,LegacyImportV1
from veriabstain_eval.workers import digest


def evidence():
    return {'schema_version':1,'predicate':'erc20.allowance','chain_id':97,'target':'0x'+'12'*20,
            'arguments':{'owner':'0x'+'34'*20,'spender':'0x'+'56'*20},'block_number':10,
            'block_hash':'0x'+'ab'*32,'value':0,'source':'legacy-fixture',
            'assurance':'SIMULATED_READ','observed_at':990,'finalized':True,
            'canonical':True,'abi_supported':True,'error':None,'conflicting':False}


def receipt():
    return {'accepted_analysis':False,'reason':'OUTPUT_VALUE_MISMATCH',
            'recommendation':'ESCALATE','execution_authorized':False,'transactions':0,'model_calls':0}


def test_evidence_import_preserves_payload_without_upgrading_missing_context():
    original=evidence();saved=copy.deepcopy(original)
    imported=import_legacy(original,source_format='legacy_evidence_v1')
    assert original==saved and imported.source_payload==original
    assert imported.source_digest==digest(original)
    original['value']=999
    assert imported.source_payload['value']==0
    result=assess_legacy_import(imported)
    assert result['snapshot_status']=='UNSUPPORTED_OR_INCONCLUSIVE'
    assert result['temporal_status']=='UNKNOWN' and not result['truth_verified']
    assert 'block_timestamp' in result['missing_context']


def test_file_receipt_and_callback_stay_distinct():
    original=receipt()
    file={'receipt':original,'receipt_digest':digest(original),'integrity':'LOCAL_CONTENT_DIGEST_NOT_SIGNATURE'}
    record=import_legacy(file,source_format='legacy_file_receipt_v1')
    assert record.source_payload==file
    callback={**original,'reason':'SDK_VERIFICATION_FAILED','submission_performed':False}
    other=import_legacy(callback,source_format='legacy_callback_receipt_v1')
    assert other.source_payload==callback and other.source_format!=record.source_format
    assert assess_legacy_import(other)['reason']=='HISTORICAL_RECEIPT_ONLY'
    with pytest.raises(ValueError):import_legacy(callback,source_format='legacy_file_receipt_v1')


@pytest.mark.parametrize('change',[
    {'schema_version':True},{'value':True},{'source':'https://rpc.example/?key=hidden'},
    {'assurance':'CRYPTOGRAPHIC_PROOF'},{'extra':'unsupported'}])
def test_bad_legacy_records_rejected(change):
    value=evidence();value.update(change)
    with pytest.raises(ValueError):import_legacy(value,source_format='legacy_evidence_v1')


def test_revalidate_mutated_wrapper_and_duplicate_json_keys():
    imported=import_legacy(evidence(),source_format='legacy_evidence_v1')
    imported.source_payload['value']=1
    with pytest.raises(ValueError):assess_legacy_import(imported)
    raw=json.dumps(evidence())[:-1]+',"value":0}'
    with pytest.raises(ValueError):import_legacy(raw,source_format='legacy_evidence_v1')


def test_changed_digest_or_version_cannot_masquerade_as_compatibility():
    record=import_legacy(evidence(),source_format='legacy_evidence_v1').model_dump()
    record['source_digest']='0'*64
    with pytest.raises(ValueError):LegacyImportV1.model_validate(record)
    record=import_legacy(evidence(),source_format='legacy_evidence_v1').model_dump()
    record['compatibility_version']='2.0'
    with pytest.raises(ValueError):LegacyImportV1.model_validate(record)


def complete_context():
    from veriabstain_eval.evidence_envelope import expected_contract_identity,expected_decoding_identity
    old=evidence()
    old['target']='0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565'
    calldata='0xdd62ed3e'+'0'*24+old['arguments']['owner'][2:]+'0'*24+old['arguments']['spender'][2:]
    observation={'observed_at':990,'block_timestamp':980,'max_block_age_seconds':120,
                 'max_observation_age_seconds':300,'finalized':True,'canonical':True,
                 'abi_supported':True,'error':'NONE','conflicting':False,
                 'assurance':'SIMULATED_READ','source_id':'legacy-fixture',
                 'historical_state_capability':'AVAILABLE'}
    identity=expected_contract_identity(old['predicate'])
    decoding={**expected_decoding_identity(old['predicate']),'calldata':calldata,'return_data':'0x'+'0'*64}
    reproduction={'rpc_method':'eth_call','block_reference':'NUMBER_AND_HASH_PINNED','chain_id':97,
                  'target':old['target'],'block_number':10,'block_hash':old['block_hash'],'calldata':calldata}
    return old,{'observation':observation,'identity':identity,'decoding':decoding,'reproduction':reproduction}


def test_explicit_enrichment_preserves_original_and_no_assurance_upgrade():
    from veriabstain_eval.envelope_compat import build_envelope_from_legacy
    from veriabstain_eval.evidence_envelope import assess_envelope
    old,context=complete_context()
    record=import_legacy(old,source_format='legacy_evidence_v1');before=record.model_dump()
    envelope=build_envelope_from_legacy(record,**context)
    assert record.model_dump()==before
    assert envelope.claim.value==old['value'] and envelope.observation.assurance==old['assurance']
    result=assess_envelope(envelope,now=1000)
    assert result.snapshot_status=='VALID_AT_SNAPSHOT' and result.authenticity=='NOT_ESTABLISHED'
    assert result.execution_authorized is False and result.current_use_allowed is False
    assert assess_legacy_import(record)['snapshot_status']=='UNSUPPORTED_OR_INCONCLUSIVE'


@pytest.mark.parametrize('field,value',[
    ('assurance','RPC_FINALIZED_READ'),('source_id','other-provider'),('observed_at',1000),
    ('finalized',False),('canonical',False),('abi_supported',False),('conflicting',True),
    ('error','RPC_UNAVAILABLE')])
def test_enrichment_cannot_override_observed_legacy_facts(field,value):
    from veriabstain_eval.envelope_compat import build_envelope_from_legacy
    old,context=complete_context();context['observation'][field]=value
    record=import_legacy(old,source_format='legacy_evidence_v1')
    with pytest.raises(ValueError):build_envelope_from_legacy(record,**context)


def test_enrichment_requires_context_and_receipts_are_not_evidence():
    from veriabstain_eval.envelope_compat import build_envelope_from_legacy
    old,context=complete_context();record=import_legacy(old,source_format='legacy_evidence_v1')
    context['observation'].pop('block_timestamp')
    with pytest.raises(ValueError):build_envelope_from_legacy(record,**context)
    callback={**receipt(),'submission_performed':False}
    other=import_legacy(callback,source_format='legacy_callback_receipt_v1')
    with pytest.raises(ValueError):build_envelope_from_legacy(other,**context)
