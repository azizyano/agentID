# Strict analysis deliverable validation

Owner approved this narrower utility implementation on2026-11-20 after the
exploratory comparison failed to establish refusal-recovery value. This approval
does not change the original experimental result or authorize broader G2 work.

Run the entirely synthetic example from this repository:

```powershell
.\.venv\Scripts\python.exe tools\validate_deliverable.py --output examples/deliverable-validation/output.json --authorization examples/deliverable-validation/authorization.json --evidence examples/deliverable-validation/evidence.json --now 1000
```

Exit0 means the analysis matches supplied authorized context and evidence;
exit2 means rejection/escalation. The example uses a fixed fixture timestamp,
addresses and block, not live BSC data. Real callers must supply a trusted current
timestamp, independent authorization, and independently collected evidence.
Never accept those inputs from the untrusted worker being validated.

The supported predicates are `erc20.allowance` and `erc8183.job_status`. Output
must contain exactly schema_version, predicate, chain_id, target, arguments,
block_number, block_hash and value. Values are strict uint256 allowance integers
or supported job-status names. Unknown fields and duplicate JSON keys fail.

Validation binds predicate, chain, contract and exact arguments to authorization
and evidence; it also binds output to the evidence block number/hash and value.
Addresses compare case-insensitively. Authorization needs `analyze`, an unexpired
deadline and zero asset-spend scope. Evidence needs explicit assurance, source,
finality/canonicality/ABI support, no errors/conflicts, and age0..300seconds.
Callers may shorten freshness but cannot extend it beyond300seconds.

Receipts expose only reason, accepted_analysis, recommendation, assurance and
canonical record digests. They omit raw output, addresses and tool text.
`execution_authorized` is always false. A digest binds content; it does not
authenticate who supplied it or prove the predicate. Public hashes can still
reveal predictable inputs through guessing and are not confidentiality tools.

No RPC, model, wallet, submission, recovery or retry runs in this validator.
`RPC_FINALIZED_READ` means provider trust; `SIMULATED_READ` remains simulated.
The validator checks caller assertions about evidence quality; it does not
independently establish finality, ABI correspondence or canonicality. Independent
evidence collection/integration remains a separate step.

Original comparison prompts, fixtures, evaluator and recorded failures remain
unchanged. The new validator is opt-in and standalone; no product-value or
production-readiness claim follows from its tests.
