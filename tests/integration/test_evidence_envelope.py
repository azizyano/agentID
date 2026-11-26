"""G1 envelope contract checks; fixed golden ABI, not a scored mutation corpus.

Golden return bytes below are assembled from the documented ABI word layout,
independently of the envelope's decoder or expected-outcome implementation.
No network, model, wallet, historical fixture or evaluation artifact is used.
"""
import copy

import pytest
from eth_utils import keccak
from pydantic import ValidationError

from veriabstain_eval.evidence_envelope import (
    EvidenceEnvelopeV1,
    ObservationContext,
    SnapshotClaim,
    assess_envelope,
    expected_contract_identity,
    expected_decoding_identity,
)
from veriabstain_eval.deliverables import Authorization

TOKEN = '0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565'
COMMERCE = '0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE'
OWNER = '0xb16b77C16773DEF8fA279A1228Eba9308eCD7841'
PROVIDER = '0x7d5E9Fc2D79ed404fbfDe64f93b199cFCC1bB3c1'
ROUTER = '0xD7d36D66d2F1B608A0F943f722D27e3744f66F25'
BLOCK_HASH = '0x' + 'ab' * 32


def word(value):
    return value.to_bytes(32, 'big').hex()


def address_word(value):
    return '0' * 24 + value[2:].lower()


def golden_job_return(status=3, job_id=1766):
    # One dynamic tuple return starts with offset32. Description is tuple field4,
    # hence its head offset is11words=352bytes. The status is tuple field7.
    description = b'G1 independently specified golden job'
    description_tail = word(len(description)) + description.hex()
    description_tail += '00' * ((32 - len(description) % 32) % 32)
    head = [word(job_id), address_word(OWNER), address_word(PROVIDER),
            address_word(ROUTER), word(352), word(10**18), word(2000),
            word(status), address_word(ROUTER), word(995), '00' * 32]
    return '0x' + word(32) + ''.join(head) + description_tail


def envelope(predicate='erc20.allowance'):
    job = predicate == 'erc8183.job_status'
    target = COMMERCE if job else TOKEN
    arguments = {'job_id': 1766} if job else {'owner': OWNER, 'spender': COMMERCE}
    selector = ('0x' + keccak(text='getJob(uint256)')[:4].hex()) if job else '0xdd62ed3e'
    calldata = selector + (word(1766) if job else address_word(OWNER) + address_word(COMMERCE))
    raw = golden_job_return() if job else '0x' + word(100)
    return {
        'kind': 'veriabstain.evidence_envelope', 'envelope_version': 1,
        'claim': {'predicate': predicate, 'chain_id': 97, 'target': target,
                  'arguments': arguments, 'block_number': 10, 'block_hash': BLOCK_HASH,
                  'value': 'COMPLETED' if job else 100},
        'observation': {'observed_at': 1000, 'block_timestamp': 990,
                        'max_block_age_seconds': 120, 'max_observation_age_seconds': 300,
                        'finalized': True, 'canonical': True, 'abi_supported': True,
                        'error': 'NONE', 'conflicting': False,
                        'assurance': 'SIMULATED_READ', 'source_id': 'g1-golden-fixture',
                        'historical_state_capability': 'AVAILABLE'},
        'identity': expected_contract_identity(predicate),
        'decoding': {**expected_decoding_identity(predicate), 'calldata': calldata,
                     'return_data': raw},
        'reproduction': {'rpc_method': 'eth_call', 'block_reference': 'NUMBER_AND_HASH_PINNED',
                         'chain_id': 97, 'target': target, 'block_number': 10,
                         'block_hash': BLOCK_HASH, 'calldata': calldata},
    }


def authorization(package, **changes):
    claim = package['claim']
    return {**{key: copy.deepcopy(claim[key]) for key in ('predicate', 'chain_id', 'target', 'arguments')},
            'allowed_actions': ['analyze'], 'deadline': 1100, 'max_asset_spend': 0,
            **changes}


@pytest.mark.parametrize('predicate', ['erc20.allowance', 'erc8183.job_status'])
def test_independent_golden_abi_snapshot(predicate):
    package = envelope(predicate)
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'VALID_AT_SNAPSHOT'
    assert result.temporal_status == 'CURRENT'
    assert result.authorization_status == 'NOT_PROVIDED'
    assert result.current_use_allowed is False
    assert result.execution_authorized is False
    assert result.assurance == 'SIMULATED_READ'


@pytest.mark.parametrize('predicate', ['erc20.allowance', 'erc8183.job_status'])
def test_false_claim_is_invalid_at_the_observed_snapshot(predicate):
    package = envelope(predicate)
    package['claim']['value'] = 'OPEN' if predicate == 'erc8183.job_status' else 101
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'INVALID_AT_SNAPSHOT'
    assert result.current_use_allowed is False and result.execution_authorized is False


def test_historical_validity_is_not_current_revalidation():
    package = envelope()
    old = assess_envelope(package, now=1200, authorization=authorization(package, deadline=2000))
    assert old.snapshot_status == 'VALID_AT_SNAPSHOT'
    assert old.temporal_status == 'REVALIDATION_REQUIRED'
    assert old.current_use_allowed is False and old.execution_authorized is False


@pytest.mark.parametrize('predicate', ['erc20.allowance', 'erc8183.job_status'])
def test_historical_incorrect_claim_preserves_snapshot_invalidity(predicate):
    package = envelope(predicate)
    package['claim']['value'] = 'OPEN' if predicate == 'erc8183.job_status' else 101
    result = assess_envelope(package, now=1200,
                             authorization=authorization(package, deadline=2000))
    assert result.snapshot_status == 'INVALID_AT_SNAPSHOT'
    assert result.temporal_status == 'REVALIDATION_REQUIRED'
    assert result.reason == 'CLAIM_MISMATCH'
    assert result.current_use_allowed is False and result.execution_authorized is False


def test_analysis_authorization_never_expands_to_execution():
    package = envelope()
    result = assess_envelope(package, now=1000, authorization=authorization(package))
    assert result.authorization_status == 'CURRENTLY_AUTHORIZED'
    assert result.current_use_allowed is True
    assert result.execution_authorized is False
    blocked = assess_envelope(package, now=1000, authorization=authorization(package, deadline=1000))
    assert blocked.authorization_status == 'BLOCKED' and blocked.current_use_allowed is False


@pytest.mark.parametrize('capability,error', [
    ('PRUNED', 'PRUNED_STATE'), ('MISSING_STATE', 'MISSING_STATE'),
    ('UNSUPPORTED', 'RPC_UNAVAILABLE'), ('UNKNOWN', 'RPC_UNAVAILABLE'),
])
def test_unavailable_raw_transcript_is_inconclusive(capability, error):
    package = envelope()
    package['observation']['historical_state_capability'] = capability
    package['observation']['error'] = error
    package['decoding']['return_data'] = None
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'
    assert result.current_use_allowed is False and result.execution_authorized is False


@pytest.mark.parametrize('capability,error', [
    ('PRUNED', 'PRUNED_STATE'), ('MISSING_STATE', 'MISSING_STATE'),
    ('UNSUPPORTED', 'RPC_UNAVAILABLE'), ('UNKNOWN', 'RPC_UNAVAILABLE'),
])
def test_provider_capability_failure_is_not_merely_a_malformed_schema(capability, error):
    package = envelope()
    package['observation']['historical_state_capability'] = capability
    package['observation']['error'] = error
    package['decoding']['return_data'] = '0x'
    # Empty hex is structurally supported; this must exercise observation
    # capability handling rather than the schema's missing/null-data path.
    EvidenceEnvelopeV1.model_validate(package)
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'
    assert result.reason == 'UNSUPPORTED_OBSERVATION'
    assert result.current_use_allowed is False and result.execution_authorized is False


def test_quality_flags_do_not_replace_the_raw_transcript():
    package = envelope()
    del package['decoding']['return_data']
    assert assess_envelope(package, now=1000).snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'


@pytest.mark.parametrize('section,field,value', [
    ('claim', 'chain_id', True), ('claim', 'block_number', True), ('claim', 'value', True),
    ('observation', 'observed_at', True), ('observation', 'max_block_age_seconds', 121),
    ('observation', 'max_observation_age_seconds', 301),
    ('observation', 'assurance', 'CRYPTOGRAPHIC_PROOF'),
])
def test_nested_schema_strictness(section, field, value):
    package = envelope()
    package[section][field] = value
    with pytest.raises(ValidationError):
        EvidenceEnvelopeV1.model_validate(package)


def test_version_and_unknown_fields_are_strict():
    package = envelope()
    package['envelope_version'] = True
    with pytest.raises(ValidationError):
        EvidenceEnvelopeV1.model_validate(package)
    package = envelope()
    package['execute_transfer'] = True
    with pytest.raises(ValidationError):
        EvidenceEnvelopeV1.model_validate(package)


@pytest.mark.parametrize('change', ['chain', 'target', 'implementation', 'abi', 'selector'])
def test_exact_reviewed_scope_and_decoding_are_required(change):
    package = envelope('erc8183.job_status')
    if change == 'chain':
        package['claim']['chain_id'] = 56
    elif change == 'target':
        package['claim']['target'] = '0x' + '11' * 20
    elif change == 'implementation':
        package['identity']['proxy_implementation'] = '0x' + '11' * 20
    elif change == 'abi':
        package['decoding']['abi_sha256'] = '0' * 64
    else:
        package['decoding']['selector'] = '0x00000000'
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'
    assert result.execution_authorized is False


def test_review_helpers_match_independently_recorded_deployment_pins():
    token = expected_contract_identity('erc20.allowance')
    commerce = expected_contract_identity('erc8183.job_status')
    assert token['chain_id'] == commerce['chain_id'] == 97
    assert token['target'].lower() == TOKEN.lower()
    assert token['target_code_hash'] == '0xae12b1d61f7ed4febf649ccf319cb49a0e921cca3739dcb01b47d316049d46ff'
    assert token['proxy_implementation'] is None and token['implementation_code_hash'] is None
    assert commerce['target'].lower() == COMMERCE.lower()
    assert commerce['proxy_implementation'].lower() == '0x55c3826b39a0f671b2c3e5d0f1372cad0b911421'
    assert commerce['implementation_code_hash'] == '0xb42935ea4e89b470ea5049cf66d7f1003a5c8d452aef72d78c666577e828380b'
    assert expected_decoding_identity('erc20.allowance')['selector'] == '0xdd62ed3e'


def test_existing_job_id_must_match_raw_return():
    package = envelope('erc8183.job_status')
    package['decoding']['return_data'] = golden_job_return(job_id=0)
    assert assess_envelope(package, now=1000).snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'


def test_unavailable_abi_fails_closed_without_exception_text(monkeypatch):
    package = envelope()

    def unavailable(_name):
        raise OSError('secret/provider/path')

    monkeypatch.setattr('veriabstain_eval.evidence_envelope.load_abi', unavailable)
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'
    assert result.reason == 'UNSUPPORTED_DECODING'
    assert result.current_use_allowed is False and result.execution_authorized is False
    assert 'secret' not in result.model_dump_json()


@pytest.mark.parametrize('as_top_model', [False, True])
def test_constructed_nested_observation_cannot_expand_freshness_or_finality(as_top_model):
    package = envelope()
    package['observation'] = ObservationContext.model_construct(
        **{**package['observation'], 'max_block_age_seconds': 999999,
           'max_observation_age_seconds': 999999, 'finalized': 'false'})
    candidate = EvidenceEnvelopeV1.model_construct(**package) if as_top_model else package
    result = assess_envelope(candidate, now=9999,
                             authorization=authorization(package, deadline=20000))
    assert result.snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'
    assert result.current_use_allowed is False and result.execution_authorized is False


@pytest.mark.parametrize('change', [
    {'chain_id': 97.0}, {'block_number': True},
    {'arguments': {'owner': OWNER, 'spender': 123}},
    {'arguments': {'owner': OWNER, 'spender': COMMERCE, 'transfer': 'extra'}},
])
def test_constructed_nested_claim_must_be_fully_revalidated(change):
    package = envelope()
    package['claim'] = SnapshotClaim.model_construct(**{**package['claim'], **change})
    result = assess_envelope(package, now=1000)
    assert result.snapshot_status == 'UNSUPPORTED_OR_INCONCLUSIVE'
    assert result.current_use_allowed is False and result.execution_authorized is False


@pytest.mark.parametrize('change', [
    {'max_asset_spend': 100}, {'max_asset_spend': False},
    {'deadline': 20000.0}, {'deadline': '20000'}, {'allowed_actions': 'analyze'},
])
def test_constructed_authorization_cannot_bypass_strict_limits(change):
    package = envelope()
    constructed = Authorization.model_construct(**{**authorization(package, deadline=20000), **change})
    result = assess_envelope(package, now=1000, authorization=constructed)
    assert result.authorization_status == 'BLOCKED'
    assert result.current_use_allowed is False and result.execution_authorized is False
