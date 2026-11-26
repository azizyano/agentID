"""Explicit legacy imports; old formats remain unchanged and are never proofs.

These wrappers are private compatibility records, not new complete envelopes or
public receipts. They preserve historical content rather than inventing missing
call bytes, block timestamps or reviewed identities.
"""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .deliverables import Evidence
from .dataset import canonical
from .receipt_inspection import safe_receipt_shape
from .workers import digest, strict_json

LegacyFormat = Literal['legacy_evidence_v1','legacy_file_receipt_v1','legacy_callback_receipt_v1']
MISSING_EVIDENCE_CONTEXT = (
    'block_timestamp','reviewed_contract_identity','abi_and_decoding_identity',
    'raw_call_and_return_bytes','provider_capability','reproduction_inputs',
)
CALLBACK_REASONS = {
    'CONTEXT_CHANGED','RECONCILE_PENDING_ANALYSIS','UNEXPECTED_JOB','SDK_VERIFICATION_FAILED',
    'JOB_BINDING_MISMATCH','RECONCILE_FAILED_ANALYSIS',
}


def _valid_source_payload(source_format, payload):
    if source_format == 'legacy_evidence_v1':
        evidence = Evidence.model_validate(payload)
        # Stable source aliases only; never transport credential-bearing URLs.
        return re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',evidence.source) is not None
    if source_format == 'legacy_file_receipt_v1':
        return (isinstance(payload,dict) and set(payload)=={'receipt','receipt_digest','integrity'}
                and payload['integrity']=='LOCAL_CONTENT_DIGEST_NOT_SIGNATURE'
                and safe_receipt_shape(payload['receipt'])
                and payload['receipt_digest']==digest(payload['receipt']))
    if not isinstance(payload,dict):
        return False
    copy = dict(payload)
    if copy.pop('submission_performed',None) is not False:
        return False
    for field in ('cached','historical_receipt'):
        if field in copy and type(copy.pop(field)) is not bool:
            return False
    # Callback diagnostic reasons are a distinct legacy vocabulary. Map solely
    # for structural validation, preserving the original payload verbatim.
    if not isinstance(copy.get('reason'),str):
        return False
    if copy['reason'] in CALLBACK_REASONS:
        if copy.get('accepted_analysis') is not False:
            return False
        copy['reason']='CHECK_FAILED'
    return safe_receipt_shape(copy)


class LegacyImportV1(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid',frozen=True)
    kind: Literal['veriabstain.legacy_import'] = 'veriabstain.legacy_import'
    compatibility_version: Literal['1.0'] = '1.0'
    source_format: LegacyFormat
    source_payload: dict
    source_digest: str

    @model_validator(mode='after')
    def intact_source(self):
        if (len(canonical(self.source_payload).encode())>65_536
                or self.source_digest!=digest(self.source_payload)
                or not _valid_source_payload(self.source_format,self.source_payload)):
            raise ValueError('Legacy payload unsupported or inconsistent')
        return self


def import_legacy(payload, *, source_format: LegacyFormat):
    if isinstance(payload,str):
        if len(payload.encode())>65_536:
            raise ValueError('Legacy input exceeds size limit')
        payload=strict_json(payload)
    # JSON roundtrip makes an independent copy. No coercion by old schemas is
    # written back; the canonical content digest binds the exact JSON values.
    if not isinstance(payload,dict) or len(canonical(payload).encode())>65_536:
        raise ValueError('Legacy payload must be a bounded JSON object')
    original=strict_json(canonical(payload))
    return LegacyImportV1(source_format=source_format,source_payload=original,
                          source_digest=digest(original))


def assess_legacy_import(record):
    """Historical imports alone never establish a reproducible snapshot verdict."""
    record=LegacyImportV1.model_validate(record.model_dump() if isinstance(record,LegacyImportV1) else record)
    return {'snapshot_status':'UNSUPPORTED_OR_INCONCLUSIVE','temporal_status':'UNKNOWN',
            'reason':'LEGACY_CONTEXT_INCOMPLETE' if record.source_format=='legacy_evidence_v1'
                     else 'HISTORICAL_RECEIPT_ONLY',
            'missing_context':list(MISSING_EVIDENCE_CONTEXT) if record.source_format=='legacy_evidence_v1'
                              else ['original_analysis_and_evidence','reproduction_inputs'],
            'source_digest':record.source_digest,'execution_authorized':False,
            'authenticated':False,'truth_verified':False}


def build_envelope_from_legacy(record, *, observation, identity, decoding, reproduction):
    """Enrich only with explicitly supplied missing context; never infer it.

    Result is an envelope to assess, not an accepted verdict. Original assurance,
    source and observed facts cannot be overridden by an enrichment caller.
    """
    from .evidence_envelope import EvidenceEnvelopeV1
    record=LegacyImportV1.model_validate(record.model_dump() if isinstance(record,LegacyImportV1) else record)
    if record.source_format!='legacy_evidence_v1':
        raise ValueError('Receipts cannot reconstruct an evidence envelope')
    source=record.source_payload
    for field in ('observed_at','finalized','canonical','abi_supported','conflicting','assurance'):
        if observation.get(field)!=source[field] or type(observation.get(field)) is not type(source[field]):
            raise ValueError('Explicit observation contradicts legacy evidence')
    if observation.get('source_id')!=source['source']:
        raise ValueError('Source provenance cannot change during compatibility conversion')
    if (source['error'] is None) != (observation.get('error')=='NONE'):
        raise ValueError('Legacy error cannot be removed or fabricated')
    claim={k:source[k] for k in ('predicate','chain_id','target','arguments','block_number','block_hash','value')}
    return EvidenceEnvelopeV1.model_validate({'kind':'veriabstain.evidence_envelope','envelope_version':1,
        'claim':claim,'observation':observation,'identity':identity,'decoding':decoding,
        'reproduction':reproduction})
