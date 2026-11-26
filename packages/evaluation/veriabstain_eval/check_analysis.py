"""One read-only check: independent evidence, validation, private local receipt."""
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

from .chain_evidence import collect_evidence
from .deliverables import Authorization, Deliverable, scope_key, validate_deliverable
from .workers import strict_json, digest


def check_analysis(w3, authorization, output, *, collector=collect_evidence, clock=time.time):
    """The worker selects a block to check, never the evidence or supported ABI.

    Collector independently requires that block to be finalized, canonical and
    fresh, and obtains the actual value under the reviewed runtime pins.
    """
    rejected = {'accepted_analysis':False,'recommendation':'ESCALATE','execution_authorized':False}
    try:
        auth = Authorization.model_validate(authorization)
        now = int(clock())
        if now >= auth.deadline or 'analyze' not in auth.allowed_actions:
            return {**rejected,'reason':'AUTHORIZATION_BLOCKED'}
        if not isinstance(output,str) or len(output.encode()) > 16_384:
            return {**rejected,'reason':'INVALID_OUTPUT'}
        candidate = Deliverable.model_validate(strict_json(output))
        if scope_key(auth) != scope_key(candidate):
            return {**rejected,'reason':'OUTPUT_SCOPE_MISMATCH'}
        scope = {k:getattr(auth,k) for k in ('predicate','chain_id','target','arguments')}
        evidence = collector(w3,scope,now=now,pinned_block_number=candidate.block_number)
        receipt = validate_deliverable(output,auth.model_dump(),evidence,now=int(clock()))
        return {**receipt,'checked_at':int(clock()),'network_calls':'READ_ONLY',
                'transactions':0,'model_calls':0}
    except Exception:
        return {**rejected,'reason':'CHECK_FAILED','transactions':0,'model_calls':0}


def save_receipt(receipt, directory):
    """Publish complete local receipt atomically in a newly reserved directory."""
    root = Path(directory)
    root.mkdir(parents=True,exist_ok=True)
    entry = root / uuid.uuid4().hex
    entry.mkdir()  # exclusive namespace; never replace an existing receipt
    envelope = {'receipt':receipt,'receipt_digest':digest(receipt),
                'integrity':'LOCAL_CONTENT_DIGEST_NOT_SIGNATURE'}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=entry,delete=False) as target:
            temporary = Path(target.name)
            json.dump(envelope,target,indent=2,allow_nan=False)
            target.write('\n');target.flush();os.fsync(target.fileno())
        os.replace(temporary,entry/'receipt.json')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return entry/'receipt.json'
