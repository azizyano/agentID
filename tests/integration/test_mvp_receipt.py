import copy
import importlib.util
import json
from pathlib import Path

import pytest
from web3 import Web3

from veriabstain_eval.evidence_envelope import EvidenceEnvelopeV1
from veriabstain_eval.mvp_receipt import (
    ASSESSMENT_DOMAIN,
    EVIDENCE_DOMAIN,
    FUNCTION_SIGNATURE,
    prepare_receipt_plan,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/evidencelab/envelope-v1-allowance.json'
spec = importlib.util.spec_from_file_location('prepare_mvp_receipt', ROOT / 'tools/prepare_mvp_receipt.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def envelope():
    return json.loads(EXAMPLE.read_text(encoding='utf-8'))


def test_same_validated_content_and_time_produce_the_same_plan():
    first = prepare_receipt_plan(envelope(), now=1000)
    second = prepare_receipt_plan(envelope(), now=1000)
    assert first == second
    assert first.evidence_payload['domain'] == EVIDENCE_DOMAIN
    assert first.assessment_payload['domain'] == ASSESSMENT_DOMAIN
    assert first.assessment.snapshot_status == 'VALID_AT_SNAPSHOT'
    assert first.assessment.authorization_status == 'NOT_PROVIDED'
    assert first.assessment.current_use_allowed is False
    assert first.assessment.execution_authorized is False
    assert first.contract_address is None and first.transactions_sent == 0


def test_hex_casing_is_normalized_before_hashing():
    original = envelope()
    changed = copy.deepcopy(original)
    for section in ('claim', 'identity', 'reproduction'):
        changed[section]['target'] = changed[section]['target'].upper().replace('0X', '0x')
    changed['decoding']['selector'] = changed['decoding']['selector'].upper().replace('0X', '0x')
    changed['claim']['block_hash'] = changed['claim']['block_hash'].upper().replace('0X', '0x')
    changed['reproduction']['block_hash'] = changed['reproduction']['block_hash'].upper().replace('0X', '0x')
    assert prepare_receipt_plan(original, now=1000).evidence_digest == prepare_receipt_plan(changed, now=1000).evidence_digest


def test_assessment_digest_binds_evidence_digest_and_assessment_time():
    first = prepare_receipt_plan(envelope(), now=1000)
    later = prepare_receipt_plan(envelope(), now=1001)
    changed = envelope()
    changed['observation']['source_id'] = 'another-reviewed-source'
    different = prepare_receipt_plan(changed, now=1000)
    assert first.evidence_digest == later.evidence_digest
    assert first.assessment_digest != later.assessment_digest
    assert first.evidence_digest != different.evidence_digest
    assert first.assessment_digest != different.assessment_digest
    assert different.assessment_payload['evidence_digest'] == different.evidence_digest


def test_calldata_exactly_encodes_the_two_content_digests():
    plan = prepare_receipt_plan(envelope(), now=1000)
    assert plan.function_signature == FUNCTION_SIGNATURE
    assert plan.calldata[:10] == Web3.to_hex(Web3.keccak(text=FUNCTION_SIGNATURE)[:4])
    evidence_digest, assessment_digest = Web3().codec.decode(
        ['bytes32', 'bytes32'], bytes.fromhex(plan.calldata[10:])
    )
    assert Web3.to_hex(evidence_digest) == plan.evidence_digest
    assert Web3.to_hex(assessment_digest) == plan.assessment_digest
    assert plan.chain_id == 56 and plan.native_value_wei == 0


@pytest.mark.parametrize('now', [True, -1, '1000', 1.5])
def test_invalid_assessment_time_is_rejected(now):
    with pytest.raises(ValueError, match='Assessment time'):
        prepare_receipt_plan(envelope(), now=now)


def test_malformed_or_constructed_nested_models_are_revalidated():
    malformed = envelope()
    malformed['unexpected'] = 'instruction'
    with pytest.raises(ValueError, match='Evidence envelope is invalid'):
        prepare_receipt_plan(malformed, now=1000)

    constructed = EvidenceEnvelopeV1.model_construct(**envelope())
    assert isinstance(constructed.claim, dict)
    bad = constructed.model_copy(update={'envelope_version': True})
    with pytest.raises(ValueError, match='Evidence envelope is invalid'):
        prepare_receipt_plan(bad, now=1000)


def test_cli_writer_is_exclusive_and_emits_no_destination_or_transaction(tmp_path, capsys):
    output = tmp_path / 'prepared'
    code = tool.main(['--evidence', str(EXAMPLE), '--now', '1000', '--output', str(output)])
    assert code == 0
    message = json.loads(capsys.readouterr().out)
    assert message['status'] == 'MVP_RECEIPT_PREPARED'
    assert message['transactionsSent'] == 0
    plan = json.loads((output / 'receipt-plan.json').read_text(encoding='utf-8'))
    assert plan['contract_address'] is None
    assert plan['transactions_sent'] == 0
    assert tool.main(['--evidence', str(EXAMPLE), '--now', '1000', '--output', str(output)]) == 2
    assert json.loads(capsys.readouterr().err)['status'] == 'MVP_RECEIPT_PREPARATION_FAILED'


def test_cli_rejects_duplicate_json_keys_without_creating_output(tmp_path):
    source = tmp_path / 'duplicate.json'
    source.write_text('{"kind":"a","kind":"b"}', encoding='utf-8')
    output = tmp_path / 'not-created'
    assert tool.main(['--evidence', str(source), '--now', '1000', '--output', str(output)]) == 2
    assert not output.exists()
