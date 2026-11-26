# Check an analysis and save a receipt

The local command combines independent finalized testnet evidence collection and
strict validation, then saves a private receipt. No server, browser, model key or
wallet is needed.

```powershell
.\.venv\Scripts\python.exe tools\check_analysis.py --authorization path/to/current-authorization.json --analysis path/to/analysis.json
```

Authorization and analysis use the schemas in DELIVERABLE_VALIDATION.md. The
authorization is independent, current, zero-spend and analysis-only. Do not
renew or extend the old paid job's permissions to run this command.

The analysis supplies its block number/hash and claimed value. These are claims
to check, not trusted evidence. The reader independently verifies that the block
is finalized, canonical and at most120seconds old, checks the reviewed target
runtime/implementation and collects the actual predicate at that block. Scope
must first match the authorization; validation then binds block and value.

Supported scope remains the reviewed chain97 test-U allowance and commerce job
status. Other targets, old/unfinalized blocks, code changes, RPC failures and
mismatched output fail closed. Evidence is RPC_FINALIZED_READ, not a cryptographic
proof. The provider can still lie consistently.

Exit0 means ACCEPTED analysis; exit2 means ESCALATE. Both save complete receipts
under `artifacts/private/analysis-receipts/<unique-id>/receipt.json` when storage
succeeds. A storage/input failure reports ESCALATE rather than acceptance without
a receipt. Each write reserves a new directory and atomically publishes a complete
JSON file, preserving prior records. This is not an immutable or authenticated
filesystem: someone with write access can replace files and recalculate hashes.

Receipts contain verdict/reason, digests and assurance; no raw model output,
authorization content, credentials or prompts. Hashes establish local content
consistency and can disclose guessable data; they are not privacy guarantees.
Nothing is published or uploaded. Every result keeps execution_authorized=false,
transactions0 and model_calls0. Acceptance never requests a submission.

Live command smoke checks accepted a manually asserted allowance0 and rejected
an intentionally incorrect allowance1 for the same fresh finalized block. Those
checks demonstrate RPC/CLI/receipt integration, not AI behavior or product value.
The original comparison and G1 no-go remain unchanged.
