# Independent read-only evidence

The evidence reader collects its own RPC observations rather than accepting the
worker's block, ABI, status, value, or evidence-quality assertions. It supports
only chain97 and the previously reviewed test-U token and commerce deployment.
Additional chains/tokens require separate code/ABI review and explicit pins.

For allowance it checks the reviewed token runtime and uses the ERC20 ABI. For
job status it checks the commerce proxy runtime, EIP1967 implementation address
and reviewed implementation code hash, then decodes the pinned SDK's getJob
tuple. Missing jobs and unknown status values fail closed.

Every read uses one finalized block number and hash; block age must be0..120
seconds. Code/storage/calls use that same block. Chain and canonical block hash
are rechecked afterward. A provider outage or failed check returns no evidence.
No wallet, account session, model, approval, transaction or signing API is used.

Collect using independently approved, current authorization JSON conforming to
the validator's Authorization schema:

```powershell
.\.venv\Scripts\python.exe tools\collect_chain_evidence.py --authorization path/to/current-authorization.json --save artifacts/private/current-evidence.json
```

The CLI uses the fixed public BSC testnet RPC, checks the real current clock and
analysis deadline before and after collection, and refuses to overwrite an
existing evidence file. It prints only a sanitized failure if checks fail.
Do not extend an old paid-job authorization to use this tool; prepare separate
authorized read-only scope when appropriate. Included synthetic examples have
expired fixture timestamps and are not live authorizations.

Pass the new evidence file and independent worker deliverable to
`tools/validate_deliverable.py`, using the current trusted time. Evidence must
remain fresh at validation. Do not derive a worker answer from the evidence and
then call that a successful model result.

Assurance remains **RPC_FINALIZED_READ**, not an independently authenticated
state proof. A malicious provider can lie consistently about blocks, bytecode,
storage and return values. Runtime matching is correspondence to reviewed
deployment pins, not a general contract security guarantee. The caller still
owns authentic authorization, RPC trust and freshness at use time.

Live deterministic smoke observations are in
`artifacts/evidence-reader/{allowance,job-status}-smoke.json`. Those checks read
actual testnet state, construct expected outputs mechanically and pass them
through the validator. They demonstrate integration, not AI reasoning or value
over a trusted-read baseline. Existing experiment results remain unchanged.
