# Reuse the evidence cases in an existing agent test suite

Owner accepted G3's recommendation to reuse useful components rather than expand
a standalone product. This delivery adds a test helper, not a UI, hosted/API
service, registry, production callback change or G4reproduction CLI.

Add a test alongside an existing trusted, synchronous prepared-evidence checker:

```python
from veriabstain_eval.agent_contract import assert_evidence_contract
from your_agent.evidence_checks import assess_prepared_evidence

def test_prepared_evidence_contract():
    assert_evidence_contract(assess_prepared_evidence)
```

The callable contract is `assessor(package, *, now)`. It receives only the
prepared JSON package and explicit evaluation time—not expected labels or case
IDs. Return a dict or Pydantic model containing snapshot_status, temporal_status,
authorization_status, current_use_allowed and execution_authorized with exact
declared types. No output repair or arbitrary value coercion is performed.
Both the existing baseline and envelope checker work directly with this helper.

For a report rather than an assertion, use `check_evidence_contract(checker)`.
It contains all62case outcomes, failed controls, differing fields, mutation and
network-attempt flags. Unknown output values become null; raw exception messages,
addresses/endpoints and arbitrary checker text are not copied into reports.
Assertion text contains only frozen case IDs and counts.

## Test isolation and limits

Use **trusted pure checker code**, in a dedicated sequential pytest process,
with no keys/signers/model client/live-worker bootstrap attached. This helper
executes Python supplied by the caller; it is NOT a sandbox. It does not enforce
CPU/runtime limits, undo filesystem effects, block subprocesses or prevent
deliberately bypassing instrumentation. Caller owns process/runtime isolation.

During each run, ordinary socket connect, send/receive, server setup, available
sendfile/sendmsg methods, TLS I/O/handshake and standard DNS lookup methods are
blocked and counted even if the checker catches the raised exception. This
includes normal I/O on previously connected pools, not only new connections.
Alternative native transports, saved method references and subprocesses can
bypass monkeypatch instrumentation; no absolute zero-network guarantee for
arbitrary code is possible with this helper. The guard
is process-global; the helper rejects overlapping/nested runs in that process.
Do not run unrelated network work in another thread while it is active. Separate
pytest worker processes have separate guards. Guards restore when the helper exits.

Input copies and content digests detect mutation. A checker must match all five
outcomes without mutating input or attempting network access. Exceptions and
unsupported asynchronous returns fail, even if other fields look correct.
Async functions are not run/awaited by this synchronous helper; pass a pure
synchronous evidence-checking component rather than a live async agent service.

Tests reuse the fixed G2corpus and its integrity/spec checks. This is known-set
SIMULATED_READ conformance, not evidence that the checker is production-safe,
authenticates chain state, improves AI decisions, or beats the strong baseline.
No model charges, transactions or on-chain effects are part of the helper.

## Repository dependency

The helper is importable from `packages/evaluation` using this repository's
installed environment and pytest pythonpath configuration. It reads the frozen
corpus/spec from this repository. It is not a published standalone package.
Another local suite must explicitly make that source directory importable and
retain the matching corpus/spec/dependencies; no upstream SDK checkout is edited.

Integration examples/regressions are in
`tests/integration/test_agent_contract.py`. The implementation agent runs these;
the owner does not need to rerun tests for this handoff.

G3negative results remain unchanged. No UI has been started. The owner's explicit
instruction is to ask before any future UI work; this helper does not authorize it.
