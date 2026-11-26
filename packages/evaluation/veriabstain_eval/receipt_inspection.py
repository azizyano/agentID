"""Offline receipt consistency checks; no authentication, chain or truth claim."""
import re
from pathlib import Path

from .workers import digest, strict_json

REASONS = {
    'INVALID_VALIDATION_CONTEXT','INVALID_AUTHORIZATION','AUTHORIZATION_BLOCKED',
    'INVALID_EVIDENCE','EVIDENCE_SCOPE_MISMATCH','UNSUPPORTED_EVIDENCE','STALE_EVIDENCE',
    'INVALID_OUTPUT','OUTPUT_SCOPE_MISMATCH','OUTPUT_BLOCK_MISMATCH','OUTPUT_VALUE_MISMATCH',
    'MATCHED_PINNED_EVIDENCE','CHECK_FAILED',
}
FIELDS = {'schema_version','accepted_analysis','reason','recommendation','execution_authorized',
          'assurance','authorization_digest','evidence_digest','deliverable_digest','limitations',
          'checked_at','network_calls','transactions','model_calls'}
DIGEST_FIELDS = ('authorization_digest','evidence_digest','deliverable_digest')


def safe_receipt_shape(receipt):
    if not isinstance(receipt,dict) or set(receipt)-FIELDS:
        return False
    if (type(receipt.get('accepted_analysis')) is not bool or receipt.get('execution_authorized') is not False
            or receipt.get('reason') not in REASONS):
        return False
    accepted = receipt['accepted_analysis']
    if receipt.get('recommendation') != ('ACCEPT_ANALYSIS' if accepted else 'ESCALATE'):
        return False
    if (receipt.get('reason') == 'MATCHED_PINNED_EVIDENCE') != accepted:
        return False
    for field in ('transactions','model_calls'):
        if field in receipt and (type(receipt[field]) is not int or receipt[field] != 0):
            return False
    if 'checked_at' in receipt and (type(receipt['checked_at']) is not int or receipt['checked_at'] < 0):
        return False
    if 'network_calls' in receipt and receipt['network_calls'] != 'READ_ONLY':
        return False
    if 'assurance' in receipt and receipt['assurance'] not in ('SIMULATED_READ','RPC_FINALIZED_READ'):
        return False
    if 'schema_version' in receipt and (type(receipt['schema_version']) is not int or receipt['schema_version'] != 1):
        return False
    for field in DIGEST_FIELDS:
        if field in receipt and (not isinstance(receipt[field],str) or not re.fullmatch(r'[0-9a-f]{64}',receipt[field])):
            return False
    if accepted and (receipt.get('schema_version') != 1
                     or receipt.get('assurance') not in ('SIMULATED_READ','RPC_FINALIZED_READ')
                     or not all(field in receipt for field in DIGEST_FIELDS)):
        return False
    if 'limitations' in receipt and (not isinstance(receipt['limitations'],str) or len(receipt['limitations'])>1024):
        return False
    return True


def inspect_receipt(path):
    result = {'status':'INVALID_RECEIPT','authenticated':False,'truth_verified':False,
              'execution_authorized':False}
    try:
        path=Path(path)
        if path.is_symlink() or path.parent.is_symlink() or path.parent.is_junction():
            return result
        with path.open('rb') as source:
            raw=source.read(32_769)
        if len(raw)>32_768:
            return result
        envelope=strict_json(raw.decode('utf-8'))
        if (not isinstance(envelope,dict) or set(envelope)!={'receipt','receipt_digest','integrity'}
                or envelope['integrity']!='LOCAL_CONTENT_DIGEST_NOT_SIGNATURE'
                or not isinstance(envelope['receipt_digest'],str)
                or not re.fullmatch(r'[0-9a-f]{64}',envelope['receipt_digest'])):
            return result
        receipt=envelope['receipt']
        if not safe_receipt_shape(receipt):
            return result
        if digest(receipt)!=envelope['receipt_digest']:
            return {**result,'status':'DIGEST_MISMATCH'}
        return {**result,'status':'CONTENT_CONSISTENT','accepted_analysis':receipt['accepted_analysis'],
                'reason':receipt['reason'],'assurance':receipt.get('assurance'),
                'checked_at':receipt.get('checked_at'),'historical_only':True,
                'receipt_digest':envelope['receipt_digest']}
    except (OSError,ValueError,TypeError,UnicodeError):
        return result


def list_receipts(directory,limit=100):
    if type(limit) is not int or not 1<=limit<=1000:
        raise ValueError('Receipt list limit must be1..1000')
    root=Path(directory)
    if not root.exists():
        return []
    if root.is_symlink() or root.is_junction():
        raise ValueError('Linked receipt root is unsupported')
    entries=[]
    for entry in sorted(root.iterdir(),key=lambda p:p.name):
        if re.fullmatch(r'[0-9a-f]{32}',entry.name):
            entries.append({'receipt_id':entry.name,**inspect_receipt(entry/'receipt.json')})
            if len(entries)==limit:
                break
    return entries
