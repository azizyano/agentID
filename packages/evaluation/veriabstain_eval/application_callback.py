"""Read-only SDK callback composition. No signer, submission or automatic recovery."""
import asyncio
import inspect
import json
import sqlite3
import time
from contextlib import closing

from .chain_evidence import collect_evidence
from .deliverables import Authorization, validate_deliverable
from .workers import digest


class AnalysisCallback:
    """Bind a funded job to independently approved analysis, then validate output.

    Construct with trusted configuration, not worker-provided scope or job terms.
    Keep one shared SQLite journal across redelivery/processes. A reservation left
    by crash/timeout blocks reinvocation until explicit external reconciliation.
    Returned acceptance is never a request to submit or transact.
    """
    def __init__(self, ops, w3, authorization, expected_job, worker, journal_path,
                 *, collector=collect_evidence, clock=time.time):
        self.ops, self.w3, self.worker = ops, w3, worker
        self.authorization = Authorization.model_validate(authorization).model_dump()
        required = {'jobId','client','provider','evaluator','hook','description','budget','expiredAt'}
        if (set(expected_job) != required or type(expected_job['jobId']) is not int
                or expected_job['jobId'] <= 0 or type(expected_job['budget']) is not int
                or expected_job['budget'] <= 0 or type(expected_job['expiredAt']) is not int
                or expected_job['expiredAt'] < self.authorization['deadline']):
            raise ValueError('Exact independently approved job binding required')
        self.expected = json.loads(json.dumps(expected_job))
        self.context_digest = digest({'authorization':self.authorization,'job':self.expected})
        self.path, self.collector, self.clock = journal_path, collector, clock
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS analysis_callbacks '
                       '(job_id INTEGER PRIMARY KEY,context_digest TEXT NOT NULL,state TEXT NOT NULL,receipt TEXT)')

    def reserve(self):
        with closing(sqlite3.connect(self.path,timeout=10)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT context_digest,state,receipt FROM analysis_callbacks WHERE job_id=?',
                               (self.expected['jobId'],)).fetchone()
            if prior:
                if prior[0] != self.context_digest:
                    return self.reject('CONTEXT_CHANGED')
                if prior[1] != 'COMPLETE':
                    return self.reject('RECONCILE_PENDING_ANALYSIS')
                return {**json.loads(prior[2]),'cached':True,'historical_receipt':True}
            db.execute('INSERT INTO analysis_callbacks VALUES (?,?,?,NULL)',
                       (self.expected['jobId'],self.context_digest,'RESERVED'))
        return None

    @staticmethod
    def reject(reason):
        return {'accepted_analysis':False,'reason':reason,'recommendation':'ESCALATE',
                'execution_authorized':False,'submission_performed':False}

    async def on_funded(self, discovered_job):
        if (not isinstance(discovered_job,dict) or type(discovered_job.get('jobId')) is not int
                or discovered_job['jobId'] != self.expected['jobId']):
            return self.reject('UNEXPECTED_JOB')
        previous = self.reserve()
        if previous is not None:
            return previous
        try:
            verification = await self.ops.verify_job(self.expected['jobId'])
            if not isinstance(verification,dict) or verification.get('valid') is not True:
                receipt = self.reject('SDK_VERIFICATION_FAILED')
            elif any(verification['job'].get(k) != value for k,value in self.expected.items()):
                receipt = self.reject('JOB_BINDING_MISMATCH')
            else:
                auth = json.loads(json.dumps(self.authorization))
                now = int(self.clock())
                if now >= auth['deadline'] or 'analyze' not in auth['allowed_actions']:
                    receipt = self.reject('AUTHORIZATION_BLOCKED')
                else:
                    scope = {k:auth[k] for k in ('predicate','chain_id','target','arguments')}
                    evidence = await asyncio.to_thread(self.collector,self.w3,scope,now=now)
                    # Worker receives copies; mutation cannot rewrite trusted validator inputs.
                    args = json.loads(json.dumps({'authorization':auth,'evidence':evidence}))
                    if inspect.iscoroutinefunction(self.worker):
                        output = await self.worker(args['authorization'],args['evidence'])
                    else:
                        output = await asyncio.to_thread(self.worker,args['authorization'],args['evidence'])
                    receipt = validate_deliverable(output,auth,evidence,now=int(self.clock()))
                    receipt['submission_performed'] = False
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute("UPDATE analysis_callbacks SET state='COMPLETE',receipt=? "
                           "WHERE job_id=? AND context_digest=? AND state='RESERVED'",
                           (json.dumps(receipt),self.expected['jobId'],self.context_digest))
            return receipt
        except Exception:
            # Keep reservation: even a read-only worker may incur inference costs.
            # Never log exception strings, worker output, credentials or job text.
            return self.reject('RECONCILE_FAILED_ANALYSIS')
