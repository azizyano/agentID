"""Reuse the frozen evidence cases in existing pytest suites, not live workers.

The socket guard is process-global testing instrumentation, NOT a sandbox.
Use trusted synchronous checkers in a dedicated sequential test process with no
keys/signers attached. No paid runtime or transaction functionality is provided.
"""
import copy
import inspect
import socket
import threading
import ssl
from contextlib import ExitStack
from unittest.mock import patch

from pydantic import BaseModel

from .mutation_manifest import load_corpus
from .workers import digest,strict_json

_RUN_LOCK=threading.Lock()
_VALUES={
    'snapshot_status':{'VALID_AT_SNAPSHOT','INVALID_AT_SNAPSHOT','UNSUPPORTED_OR_INCONCLUSIVE'},
    'temporal_status':{'CURRENT','REVALIDATION_REQUIRED','UNKNOWN'},
    'authorization_status':{'CURRENTLY_AUTHORIZED','BLOCKED','NOT_PROVIDED'},
}


def _safe_outcome(raw):
    if isinstance(raw,BaseModel):
        raw=BaseModel.model_dump(raw,warnings=False)
    if type(raw) is not dict:
        return {key:None for key in (*_VALUES,'current_use_allowed','execution_authorized')}
    outcome={key:raw.get(key) if type(raw.get(key)) is str and raw[key] in allowed else None
             for key,allowed in _VALUES.items()}
    for key in ('current_use_allowed','execution_authorized'):
        outcome[key]=raw.get(key) if type(raw.get(key)) is bool else None
    return outcome


def check_evidence_contract(assessor):
    """Run62frozen synthetic cases against assessor(package, *, now).

    Expected outcomes never enter the assessor; reports omit unknown output and
    exception text. Repeated calls are repeat test executions, not recovery or
    permission to reinvoke live/paid workers.
    """
    if not callable(assessor):raise TypeError('A trusted synchronous checker is required')
    if not _RUN_LOCK.acquire(blocking=False):
        raise RuntimeError('Evidence contract harness already active in this process')
    try:
        corpus,checksum=load_corpus();attempts=0;rows=[]
        def blocked(*_args,**_kwargs):
            nonlocal attempts
            attempts+=1
            raise RuntimeError('Network disabled during evidence contract tests')
        with ExitStack() as guards:
            # Existing connected pools/TLS sockets can exchange data without a
            # new connect call. Instrument their normal I/O as well as DNS.
            for owner,names in (
                (socket.socket,('connect','connect_ex','send','sendall','sendto','sendmsg','sendfile',
                                'recv','recv_into','recvfrom','recvfrom_into','recvmsg','recvmsg_into',
                                'accept','bind','listen')),
                (socket,('getaddrinfo','gethostbyname','gethostbyname_ex','gethostbyaddr')),
                (ssl.SSLSocket,('send','sendall','recv','recv_into','read','write','do_handshake','unwrap')),
            ):
                for name in names:
                    if hasattr(owner,name):guards.enter_context(patch.object(owner,name,blocked))
            for case in corpus['cases']:
                package=copy.deepcopy(strict_json(case['input_json']));before=digest(package)
                previous_attempts=attempts;error=None;outcome=_safe_outcome(None)
                try:
                    raw=assessor(package,now=case['now'])
                    if inspect.isawaitable(raw):
                        if inspect.iscoroutine(raw):raw.close()
                        error='ASYNC_CHECKER_UNSUPPORTED'
                    else:outcome=_safe_outcome(raw)
                except Exception:
                    error='CHECKER_EXCEPTION'  # Do not echo messages/addresses/headers.
                try:unchanged=before==digest(package)
                except Exception:unchanged=False
                different=[field for field,expected in case['expected'].items()
                           if type(outcome[field]) is not type(expected) or outcome[field]!=expected]
                network_attempted=attempts!=previous_attempts
                passed=not different and error is None and unchanged and not network_attempted
                rows.append({'case_id':case['case_id'],'control':case['control'],'passed':passed,
                    'expected':dict(case['expected']),'actual':outcome,'mismatched_fields':different,
                    'input_unchanged':unchanged,'network_attempted':network_attempted,'error':error})
        return {'scope':'FROZEN_SYNTHETIC_CHECKER_CONTRACT','assurance':'SIMULATED_READ',
                'corpus_sha256':checksum,'cases':len(rows),'passed':sum(row['passed'] for row in rows),
                'failed':sum(not row['passed'] for row in rows),
                'failing_controls':sum(row['control'] and not row['passed'] for row in rows),
                'blocked_network_attempts':attempts,'checker_calls':len(rows),'results':rows,
                'execution_authorized':False,'limitations':'Trusted sync test code only; process-global socket guard is not a security sandbox'}
    finally:
        _RUN_LOCK.release()


def assert_evidence_contract(assessor):
    """Drop into an existing pytest test; failure text contains only safe IDs/counts."""
    report=check_evidence_contract(assessor)
    if report['failed']:
        ids=[row['case_id'] for row in report['results'] if not row['passed']][:5]
        raise AssertionError(f"Evidence contract failed: {report['failed']}/{report['cases']}; first cases: {', '.join(ids)}")
    return report
