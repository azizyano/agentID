# Read-only application callback

`AnalysisCallback.on_funded` composes the upstream ERC8183JobOps verifier,
independent evidence collection, a worker and strict deliverable validation.
No SDK source, wallet, signer, escrow or settlement method is modified.

```python
callback = AnalysisCallback(
    ops, w3, approved_authorization, exact_approved_job, worker,
    Path("artifacts/private/analysis.sqlite3"),
)
await funded_job_watcher(ops, callback.on_funded, max_attempts=1)
```

Pass the **bound async method** `callback.on_funded`, not the instance. The SDK
checks whether the callback is an async function. SDK job fields are `jobId` and
`expiredAt`; the exact binding additionally includes client, provider, evaluator,
hook, description and budget. Configuration must come from independently approved
terms, not an untrusted worker or scanner. One instance binds one specific job.

The watcher performs its original verification; the callback verifies again
before processing, then compares the verified job with the approved binding.
Only then does it collect independent evidence, call the worker with copies and
validate output against unchanged trusted inputs and current authorization/time.
Worker scope mutation cannot change validator inputs.

A shared SQLite journal reserves the job/context before analysis. Redelivery
returns the historical receipt without calling a worker again. Concurrent or
ambiguous/crashed analysis returns ESCALATE and requires reconciliation. There
is no automatic reconsideration, inference retry or paid worker attached by
default. The caller must bound any external worker's cost and runtime separately.

Returned receipts always state `execution_authorized=false` and
`submission_performed=false`. Cached acceptance is a historical observation,
not fresh evidence or permission to submit. External submission would require a
separate authorized path and fresh SDK/evidence checks; none is implemented here.
Caller/job/clock/storage authenticity remains the application's responsibility.

Run the complete offline demonstration:

```powershell
.\.venv\Scripts\python.exe tools\run_analysis_demo.py
```

The demo uses actual SDK verification with simulated chain I/O and a scripted
worker. It demonstrates validation and single-call redelivery, not AI utility.
Its temporary journal is isolated to the demo; real callers must retain their
shared journal. Live chain evidence was checked separately in CHAIN_EVIDENCE.md.
No new funded job, model key, paid call, approval or transaction is required.

The narrower read-only utility is now composed end to end at this application
boundary. UI/API, production submission/recovery, broader deployment support and
the original refusal-recovery value gate remain outside this completed step.
