"""Versioned offline evidence envelope, separate from historical evaluation v1.

Recorded RPC data remains provider-trusted. Transcript consistency is neither
authentication nor a proof of blockchain state, and never grants execution.
"""
import hashlib
from typing import Annotated, Literal

from eth_utils.abi import collapse_if_tuple
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator
from web3 import Web3
from bnbagent.core.abis import load_abi

from .chain_evidence import TOKEN, TOKEN_HASH, COMMERCE, PROXY_HASH, JOB_STATUSES
from .dataset import canonical
from .deliverables import Authorization, Scope, scope_key
from .testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH, SOURCE_REVISION

SDK_REVISION = '260e16196931780d0370bd3a9d9b67ece744bb9d'
PINSET_ID = 'chain97-reviewed-20261120-v1'
CODEC = 'web3-eth-abi-canonical-v1'
Address = Annotated[str, Field(pattern=r'^0x[0-9a-fA-F]{40}$')]
Hash = Annotated[str, Field(pattern=r'^0x[0-9a-fA-F]{64}$')]
HexData = Annotated[str, Field(pattern=r'^0x(?:[0-9a-fA-F]{2})*$', max_length=131_074)]
Uint = Annotated[int, Field(ge=0, lt=2**256)]


class StrictRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True, revalidate_instances='always')


class SnapshotClaim(Scope):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True, revalidate_instances='always')
    block_number: Uint
    block_hash: Hash
    value: StrictInt | StrictStr

    @model_validator(mode='after')
    def supported_value(self):
        valid = (type(self.value) is int and 0 <= self.value < 2**256
                 if self.predicate == 'erc20.allowance'
                 else isinstance(self.value, str) and self.value in JOB_STATUSES)
        if not valid:
            raise ValueError('Unsupported claim value')
        return self


class ObservationContext(StrictRecord):
    observed_at: Uint
    block_timestamp: Uint
    max_block_age_seconds: int = Field(ge=0, le=120)
    max_observation_age_seconds: int = Field(ge=0, le=300)
    finalized: bool
    canonical: bool
    abi_supported: bool
    error: Literal['NONE', 'RPC_UNAVAILABLE', 'MISSING_STATE', 'PRUNED_STATE', 'DECODE_FAILED']
    conflicting: bool
    assurance: Literal['RPC_FINALIZED_READ', 'SIMULATED_READ']
    source_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
    historical_state_capability: Literal['AVAILABLE', 'PRUNED', 'MISSING_STATE', 'UNSUPPORTED', 'UNKNOWN']


class ContractIdentity(StrictRecord):
    chain_id: int = Field(gt=0)
    target: Address
    target_code_hash: Hash
    review_source_revision: str = Field(pattern=r'^[0-9a-f]{40}$')
    pinset_id: Literal['chain97-reviewed-20261120-v1']
    proxy_implementation: Address | None
    implementation_code_hash: Hash | None


class DecodingTranscript(StrictRecord):
    function_signature: str = Field(min_length=1, max_length=128)
    selector: str = Field(pattern=r'^0x[0-9a-fA-F]{8}$')
    abi_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    codec: Literal['web3-eth-abi-canonical-v1']
    sdk_revision: str = Field(pattern=r'^[0-9a-f]{40}$')
    calldata: HexData
    return_data: HexData


class ReadReproduction(StrictRecord):
    rpc_method: Literal['eth_call']
    block_reference: Literal['NUMBER_AND_HASH_PINNED']
    chain_id: int = Field(gt=0)
    target: Address
    block_number: Uint
    block_hash: Hash
    calldata: HexData


class EvidenceEnvelopeV1(StrictRecord):
    kind: Literal['veriabstain.evidence_envelope']
    envelope_version: Literal[1]
    claim: SnapshotClaim
    observation: ObservationContext
    identity: ContractIdentity
    decoding: DecodingTranscript
    reproduction: ReadReproduction

    @model_validator(mode='before')
    @classmethod
    def exact_version(cls, value):
        if isinstance(value, dict) and type(value.get('envelope_version')) is not int:
            raise ValueError('Envelope version must be integer one')
        return value


class Assessment(StrictRecord):
    envelope_kind: Literal['veriabstain.evidence_envelope'] = 'veriabstain.evidence_envelope'
    envelope_version: Literal[1] = 1
    snapshot_status: Literal['VALID_AT_SNAPSHOT', 'INVALID_AT_SNAPSHOT', 'UNSUPPORTED_OR_INCONCLUSIVE']
    temporal_status: Literal['CURRENT', 'REVALIDATION_REQUIRED', 'UNKNOWN']
    reason: Literal['INVALID_EVALUATION_TIME', 'MALFORMED_ENVELOPE', 'UNSUPPORTED_SCOPE',
                    'UNSUPPORTED_IDENTITY', 'UNSUPPORTED_DECODING', 'UNSUPPORTED_OBSERVATION',
                    'SNAPSHOT_FRESHNESS_FAILED', 'CONTEXT_MISMATCH', 'TRANSCRIPT_MISSING',
                    'TRANSCRIPT_INVALID', 'CLAIM_MISMATCH', 'SNAPSHOT_MATCHED']
    authorization_status: Literal['CURRENTLY_AUTHORIZED', 'BLOCKED', 'NOT_PROVIDED']
    current_use_allowed: bool = False
    execution_authorized: Literal[False] = False
    assurance: Literal['RPC_FINALIZED_READ', 'SIMULATED_READ'] | None = None
    authenticity: Literal['NOT_ESTABLISHED'] = 'NOT_ESTABLISHED'


def _function(predicate):
    if predicate == 'erc20.allowance':
        abi, name = load_abi('ERC20.json'), 'allowance'
    elif predicate == 'erc8183.job_status':
        abi, name = load_abi('AgenticCommerce.json'), 'getJob'
    else:
        raise ValueError('Unsupported predicate')
    entries = [entry for entry in abi if entry.get('type') == 'function' and entry.get('name') == name]
    if len(entries) != 1:
        raise ValueError('Unsupported ABI overload')
    return abi, entries[0]


def expected_decoding_identity(predicate):
    _, function = _function(predicate)
    signature = function['name'] + '(' + ','.join(collapse_if_tuple(item) for item in function['inputs']) + ')'
    return {'function_signature': signature, 'selector': Web3.to_hex(Web3.keccak(text=signature)[:4]),
            'abi_sha256': hashlib.sha256(canonical(function).encode()).hexdigest(),
            'codec': CODEC, 'sdk_revision': SDK_REVISION}


def expected_contract_identity(predicate):
    if predicate not in ('erc20.allowance', 'erc8183.job_status'):
        raise ValueError('Unsupported predicate')
    job = predicate == 'erc8183.job_status'
    return {'chain_id': 97, 'target': COMMERCE if job else TOKEN,
            'target_code_hash': PROXY_HASH if job else TOKEN_HASH,
            'review_source_revision': SOURCE_REVISION, 'pinset_id': PINSET_ID,
            'proxy_implementation': PINNED.commerce_impl if job else None,
            'implementation_code_hash': REVIEWED_COMMERCE_CODE_HASH if job else None}


def _primitive_input(value):
    """Reconstruct untrusted model trees rather than trusting model_construct.

    Pydantic's default instance handling can skip validation for nested models.
    Plain-data reconstruction also makes mutable nested model contents subject
    to the same validation as serialized inputs. Bounds prevent recursive input
    trees from bypassing the envelope's deliberately small supported surface.
    """
    remaining = 4096

    def visit(item, depth):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 16:
            raise ValueError('Unsupported input complexity')
        if isinstance(item, BaseModel):
            return visit(BaseModel.model_dump(item, mode='python', warnings=False), depth + 1)
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError('Input object keys must be strings')
            return {key: visit(content, depth + 1) for key, content in item.items()}
        if type(item) is list:
            return [visit(content, depth + 1) for content in item]
        if type(item) in (int, bool, str, type(None)):
            if isinstance(item, str) and len(item) > 131_074:
                raise ValueError('Input string exceeds supported limit')
            return item
        raise ValueError('Input must contain only supported primitive values')

    return visit(value, 0)


def _authorization_status(authorization, claim, now):
    if authorization is None:
        return 'NOT_PROVIDED'
    try:
        auth = Authorization.model_validate(_primitive_input(authorization))
        if (now < auth.deadline and 'analyze' in auth.allowed_actions
                and scope_key(auth) == scope_key(claim)):
            return 'CURRENTLY_AUTHORIZED'
    except (ValueError, TypeError):
        pass
    return 'BLOCKED'


def assess_envelope(envelope, *, now, authorization=None):
    """Offline transcript assessment, never an online recheck or execution grant.

    A recorded snapshot can remain valid after current freshness or original
    authorization expires. Missing/unsupported context stays inconclusive.
    """
    def report(reason, *, snapshot='UNSUPPORTED_OR_INCONCLUSIVE', temporal='UNKNOWN',
               auth='NOT_PROVIDED', assurance=None):
        return Assessment(snapshot_status=snapshot, temporal_status=temporal, reason=reason,
                          authorization_status=auth, assurance=assurance,
                          current_use_allowed=(snapshot == 'VALID_AT_SNAPSHOT'
                                               and temporal == 'CURRENT'
                                               and auth == 'CURRENTLY_AUTHORIZED'))

    if type(now) is not int or now < 0:
        return report('INVALID_EVALUATION_TIME', auth='BLOCKED' if authorization is not None else 'NOT_PROVIDED')
    try:
        # Revalidate every nested instance, including models embedded in dicts.
        ev = EvidenceEnvelopeV1.model_validate(_primitive_input(envelope))
    except (ValueError, TypeError):
        return report('MALFORMED_ENVELOPE', auth='BLOCKED' if authorization is not None else 'NOT_PROVIDED')
    claim, obs, identity, decoding, reproduction = ev.claim, ev.observation, ev.identity, ev.decoding, ev.reproduction
    auth = _authorization_status(authorization, claim, now)
    shared = {'auth':auth, 'assurance':obs.assurance}
    if claim.chain_id != 97:
        return report('UNSUPPORTED_SCOPE', **shared)
    try:
        expected_identity = expected_contract_identity(claim.predicate)
    except Exception:
        return report('UNSUPPORTED_IDENTITY', **shared)
    actual_identity = identity.model_dump()
    for field in ('target', 'target_code_hash', 'proxy_implementation', 'implementation_code_hash'):
        if isinstance(actual_identity[field], str):
            actual_identity[field] = actual_identity[field].lower()
        if isinstance(expected_identity[field], str):
            expected_identity[field] = expected_identity[field].lower()
    if actual_identity != expected_identity or claim.target.lower() != identity.target.lower():
        return report('UNSUPPORTED_IDENTITY', **shared)
    try:
        expected_decoding = expected_decoding_identity(claim.predicate)
    except Exception:
        # Missing/incompatible local ABI metadata is not evidence about a claim.
        # Fail inconclusive without exposing filesystem paths or provider text.
        return report('UNSUPPORTED_DECODING', **shared)
    actual_decoding = decoding.model_dump(exclude={'calldata','return_data'})
    actual_decoding['selector'] = actual_decoding['selector'].lower()
    if actual_decoding != expected_decoding:
        return report('UNSUPPORTED_DECODING', **shared)
    if (reproduction.chain_id != claim.chain_id or reproduction.target.lower() != claim.target.lower()
            or reproduction.block_number != claim.block_number
            or reproduction.block_hash.lower() != claim.block_hash.lower()
            or reproduction.calldata.lower() != decoding.calldata.lower()):
        return report('CONTEXT_MISMATCH', **shared)
    if (not obs.finalized or not obs.canonical or not obs.abi_supported or obs.conflicting
            or obs.error != 'NONE' or obs.historical_state_capability != 'AVAILABLE'):
        return report('UNSUPPORTED_OBSERVATION', **shared)
    if not 0 <= obs.observed_at - obs.block_timestamp <= obs.max_block_age_seconds:
        return report('SNAPSHOT_FRESHNESS_FAILED', **shared)
    if now < obs.observed_at:
        return report('INVALID_EVALUATION_TIME', **shared)
    temporal = ('CURRENT' if (now - obs.observed_at <= obs.max_observation_age_seconds
                              and now - obs.block_timestamp <= obs.max_block_age_seconds)
                else 'REVALIDATION_REQUIRED')
    shared['temporal'] = temporal
    if decoding.calldata == '0x' or decoding.return_data == '0x':
        return report('TRANSCRIPT_MISSING', **shared)
    try:
        abi, function = _function(claim.predicate)
        args = ([Web3.to_checksum_address(claim.arguments['owner']),
                 Web3.to_checksum_address(claim.arguments['spender'])]
                if claim.predicate == 'erc20.allowance' else [claim.arguments['job_id']])
        w3 = Web3()
        expected_calldata = w3.eth.contract(abi=abi).encode_abi(function['name'], args=args)
        if decoding.calldata.lower() != expected_calldata.lower():
            return report('CONTEXT_MISMATCH', **shared)
        raw = bytes.fromhex(decoding.return_data[2:])
        output_types = [collapse_if_tuple(item) for item in function['outputs']]
        decoded = w3.codec.decode(output_types, raw)
        if w3.codec.encode(output_types, decoded) != raw:
            return report('TRANSCRIPT_INVALID', **shared)
        if claim.predicate == 'erc20.allowance':
            value = decoded[0]
        else:
            job = decoded[0]
            if (len(job) != 11 or job[0] != claim.arguments['job_id']
                    or type(job[7]) is not int or not 0 <= job[7] < len(JOB_STATUSES)):
                return report('TRANSCRIPT_INVALID', **shared)
            value = JOB_STATUSES[job[7]]
    except Exception:
        return report('TRANSCRIPT_INVALID', **shared)
    if type(value) is not type(claim.value) or value != claim.value:
        return report('CLAIM_MISMATCH', snapshot='INVALID_AT_SNAPSHOT', **shared)
    return report('SNAPSHOT_MATCHED', snapshot='VALID_AT_SNAPSHOT', **shared)
