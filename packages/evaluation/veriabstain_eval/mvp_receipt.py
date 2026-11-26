"""Deterministic unsigned receipt preparation for the Agent ID MVP.

The resulting digests establish content consistency only. They do not prove
truth, authorship, authorization, eligibility, or successful on-chain storage.
"""
import hashlib
import re
from typing import Literal

from pydantic import Field
from web3 import Web3

from .dataset import canonical
from .evidence_envelope import (
    Assessment,
    EvidenceEnvelopeV1,
    HexData,
    StrictRecord,
    _primitive_input,
    assess_envelope,
)

HASH_ALGORITHM = 'sha256-canonical-json-v1'
EVIDENCE_DOMAIN = 'veriabstain.mvp.evidence.v1'
ASSESSMENT_DOMAIN = 'veriabstain.mvp.assessment.v1'
FUNCTION_SIGNATURE = 'recordAssessment(bytes32,bytes32)'
HEX_VALUE = re.compile(r'^0x(?:[0-9a-fA-F]{2})+$')


class ReceiptPlan(StrictRecord):
    schema_version: Literal[1] = 1
    hash_algorithm: Literal['sha256-canonical-json-v1'] = HASH_ALGORITHM
    evidence_digest: str = Field(pattern=r'^0x[0-9a-f]{64}$')
    assessment_digest: str = Field(pattern=r'^0x[0-9a-f]{64}$')
    assessed_at: int = Field(ge=0)
    assessment: Assessment
    function_signature: Literal['recordAssessment(bytes32,bytes32)'] = FUNCTION_SIGNATURE
    calldata: HexData
    chain_id: Literal[56] = 56
    native_value_wei: Literal[0] = 0
    contract_address: Literal[None] = None
    transactions_sent: Literal[0] = 0
    evidence_payload: dict
    assessment_payload: dict
    integrity: Literal['CONTENT_DIGESTS_NOT_TRUTH_OR_PERMISSION'] = (
        'CONTENT_DIGESTS_NOT_TRUTH_OR_PERMISSION'
    )


def _normalize(value):
    """Normalize validated JSON values without changing non-hex text."""
    if type(value) is dict:
        return {key: _normalize(value[key]) for key in sorted(value)}
    if type(value) is list:
        return [_normalize(item) for item in value]
    if type(value) is str and HEX_VALUE.fullmatch(value):
        return value.lower()
    return value


def _content_digest(payload):
    return '0x' + hashlib.sha256(canonical(payload).encode('utf-8')).hexdigest()


def prepare_receipt_plan(envelope, *, now):
    """Validate, reassess, hash, and ABI-encode one unsigned receipt plan."""
    if type(now) is not int or now < 0:
        raise ValueError('Assessment time must be a nonnegative integer')
    try:
        validated = EvidenceEnvelopeV1.model_validate(_primitive_input(envelope))
    except (ValueError, TypeError) as error:
        raise ValueError('Evidence envelope is invalid') from error

    assessment = assess_envelope(validated, now=now, authorization=None)
    if (
        assessment.reason in {'INVALID_EVALUATION_TIME', 'MALFORMED_ENVELOPE'}
        or assessment.authorization_status != 'NOT_PROVIDED'
        or assessment.current_use_allowed is not False
        or assessment.execution_authorized is not False
    ):
        raise ValueError('Evidence assessment is not safely recordable')

    evidence_payload = _normalize({
        'domain': EVIDENCE_DOMAIN,
        'envelope': validated.model_dump(mode='json'),
    })
    evidence_digest = _content_digest(evidence_payload)
    assessment_payload = _normalize({
        'domain': ASSESSMENT_DOMAIN,
        'evidence_digest': evidence_digest,
        'assessed_at': now,
        'assessment': assessment.model_dump(mode='json'),
    })
    assessment_digest = _content_digest(assessment_payload)

    selector = Web3.keccak(text=FUNCTION_SIGNATURE)[:4]
    arguments = Web3().codec.encode(
        ['bytes32', 'bytes32'],
        [bytes.fromhex(evidence_digest[2:]), bytes.fromhex(assessment_digest[2:])],
    )
    return ReceiptPlan(
        evidence_digest=evidence_digest,
        assessment_digest=assessment_digest,
        assessed_at=now,
        assessment=assessment,
        calldata=Web3.to_hex(selector + arguments),
        evidence_payload=evidence_payload,
        assessment_payload=assessment_payload,
    )


def validate_receipt_plan(value):
    """Rebuild a serialized receipt plan and reject any content or calldata drift."""
    try:
        plan = ReceiptPlan.model_validate(_primitive_input(value))
        rebuilt = prepare_receipt_plan(
            plan.evidence_payload['envelope'],
            now=plan.assessed_at,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Receipt plan is invalid') from error
    if plan.model_dump(mode='json') != rebuilt.model_dump(mode='json'):
        raise ValueError('Receipt plan does not match its evidence payload')
    return plan
