"""Standalone read-only deliverable validation; never grants execution permission."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from .workers import digest, strict_json

ADDRESS = r'^0x[0-9a-fA-F]{40}$'
HASH = r'^0x[0-9a-fA-F]{64}$'
STATUSES = {'OPEN', 'FUNDED', 'SUBMITTED', 'COMPLETED', 'REJECTED', 'EXPIRED'}


class Scope(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    predicate: Literal['erc20.allowance', 'erc8183.job_status']
    chain_id: int = Field(gt=0)
    target: str = Field(pattern=ADDRESS)
    arguments: dict[str, StrictInt | StrictStr]

    @model_validator(mode='after')
    def arguments_match(self):
        import re
        if self.predicate == 'erc20.allowance':
            valid = (set(self.arguments) == {'owner', 'spender'} and
                     all(isinstance(v, str) and re.fullmatch(ADDRESS, v) for v in self.arguments.values()))
        else:
            value = self.arguments.get('job_id')
            valid = set(self.arguments) == {'job_id'} and type(value) is int and 0 < value < 2**256
        if not valid:
            raise ValueError('Arguments do not match supported predicate')
        return self


class Authorization(Scope):
    allowed_actions: list[str]
    deadline: int = Field(ge=0)
    max_asset_spend: Literal[0]

    @model_validator(mode='before')
    @classmethod
    def exact_spend_type(cls, value):
        if isinstance(value, dict) and type(value.get('max_asset_spend')) is not int:
            raise ValueError('Spend limit must be exact integer zero')
        return value


class Deliverable(Scope):
    schema_version: Literal[1]
    block_number: int = Field(ge=0)
    block_hash: str = Field(pattern=HASH)
    value: StrictInt | StrictStr

    @model_validator(mode='before')
    @classmethod
    def exact_version_type(cls, value):
        if isinstance(value, dict) and type(value.get('schema_version')) is not int:
            raise ValueError('Schema version must be integer one')
        return value

    @model_validator(mode='after')
    def value_matches(self):
        if self.predicate == 'erc20.allowance':
            valid = type(self.value) is int and 0 <= self.value < 2**256
        else:
            valid = isinstance(self.value, str) and self.value in STATUSES
        if not valid:
            raise ValueError('Value does not match supported predicate')
        return self


class Evidence(Deliverable):
    source: str = Field(min_length=1, max_length=256)
    assurance: Literal['RPC_FINALIZED_READ', 'SIMULATED_READ']
    observed_at: int = Field(ge=0)
    finalized: bool
    canonical: bool
    abi_supported: bool
    error: str | None
    conflicting: bool


def scope_key(value):
    return (value.predicate, value.chain_id, value.target.lower(),
            tuple(sorted((k, v.lower() if isinstance(v, str) else v) for k, v in value.arguments.items())))


def validate_deliverable(output, authorization, evidence, *, now, max_age_seconds=300):
    """Validate against caller-supplied trusted context, without fetching or submitting.

    Caller must establish evidence provenance and canonicality independently.
    Acceptance means only that these supplied records match, not proof of truth.
    Raw untrusted output is never copied into a validation receipt.
    """
    def report(reason, accepted=False, **fields):
        return {'schema_version': 1, 'accepted_analysis': accepted, 'reason': reason,
                'recommendation': 'ACCEPT_ANALYSIS' if accepted else 'ESCALATE',
                'execution_authorized': False, **fields}

    if (type(now) is not int or now < 0 or type(max_age_seconds) is not int
            or not 0 <= max_age_seconds <= 300):
        return report('INVALID_VALIDATION_CONTEXT')
    try:
        auth = Authorization.model_validate(authorization)
    except (ValueError, TypeError):
        return report('INVALID_AUTHORIZATION')
    if now >= auth.deadline or 'analyze' not in auth.allowed_actions:
        return report('AUTHORIZATION_BLOCKED')
    try:
        ev = Evidence.model_validate(evidence)
    except (ValueError, TypeError):
        return report('INVALID_EVIDENCE')
    if scope_key(auth) != scope_key(ev):
        return report('EVIDENCE_SCOPE_MISMATCH')
    if (ev.error is not None or ev.conflicting or not ev.source.strip()
            or not ev.finalized or not ev.canonical or not ev.abi_supported):
        return report('UNSUPPORTED_EVIDENCE')
    if not 0 <= now - ev.observed_at <= max_age_seconds:
        return report('STALE_EVIDENCE')
    try:
        if not isinstance(output, str) or len(output.encode()) > 16_384:
            return report('INVALID_OUTPUT')
        result = Deliverable.model_validate(strict_json(output))
    except (ValueError, TypeError):
        return report('INVALID_OUTPUT')
    if scope_key(result) != scope_key(auth):
        return report('OUTPUT_SCOPE_MISMATCH')
    if result.block_number != ev.block_number or result.block_hash.lower() != ev.block_hash.lower():
        return report('OUTPUT_BLOCK_MISMATCH')
    if type(result.value) is not type(ev.value) or result.value != ev.value:
        return report('OUTPUT_VALUE_MISMATCH')
    return report('MATCHED_PINNED_EVIDENCE', True, assurance=ev.assurance,
                  authorization_digest=digest(auth.model_dump()),
                  evidence_digest=digest(ev.model_dump()), deliverable_digest=digest(result.model_dump()),
                  limitations='Caller-supplied evidence; hashes establish consistency, not truth or permission')
