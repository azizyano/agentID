# Run locally

The local `.venv` is installed. From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe tools\run_g1a.py
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: 40/40 fixture scenarios and 217 current project tests. Latest test evidence is under `artifacts/testnet/funding-session-tests.xml`; first-part reports remain under `artifacts/part1/`. The fixture runner exits nonzero on unexpected outcomes or observed simulated unauthorized/duplicate effects.

The manifest and SHA-256 sidecar are frozen under `fixtures/`. The runner verifies the checksum before execution. Do not regenerate it to hide failures. `tools/freeze_g1a.py` refuses to replace the existing manifest.

## Recreate the environment

With Python 3.12 and uv installed:

```powershell
py -3.12 -m venv .venv
uv pip sync requirements-test.lock --python .venv/Scripts/python.exe --cache-dir .research/uv-cache
```

Installation needs network access. The lock pins runtime/test dependencies and the SDK revision; isolated package-build dependencies are not locked. Cross-platform and bit-for-bit reproducibility are untested.

## Upstream compatibility

The ignored `.research/bnbagent-sdk` checkout is pinned. From its `python` directory:

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest tests/test_funded_watcher_verification.py tests/test_erc8183_job_ops.py tests/test_erc8183_schema.py -q -o addopts= -o asyncio_default_fixture_loop_scope=function
```

Expected: 149 tests, a subset of upstream coverage.

## Limits

Discovery and verification use real SDK code. Contract reads, evidence, and proposed submissions are synthetic. No transaction signer is attached. Ephemeral accounts sign local negotiation fixtures only and are never saved. The fixture execution blocks network connections. Before that guard, Windows asyncio creates an internal wake-up socket; Codex's sandbox blocked it on this computer, requiring approved local execution outside the sandbox.

No model runs, production recovery, or economic benefits have been demonstrated. These tests need no wallet credentials or model API keys.

## Worker comparison requests

```powershell
.\.venv\Scripts\python.exe tools\run_comparison.py
```

Exports 200 pending requests without calling a model. See [protocol and replay format](WORKER_PROTOCOL.md). Keep `artifacts/g1b/comparison.sqlite3` to resume the same experiment. It is ignored by Git. Model selection is deferred.

Exit code 2 means responses are pending; 0 means replay processing completed; 1 means an input/state/output error. In PowerShell, inspect `$LASTEXITCODE`. `summary.json` is the artifact completion marker: use exports only when `artifacts_complete` is true and `run_status` is AWAITING_RESPONSES or COMPLETED_REPLAY. Errors clear generated exports and preserve the SQLite ledger. An unknown response ID is an error.

## Testnet job preparation

See [TESTNET_JOB.md](TESTNET_JOB.md) for the public-input draft, offline schema, source comparison, faucet claim, and manually signed staged flow. The application deployment pin reflects the reviewed source/runtime match; upstream SDK files remain unchanged. No job transaction is ready until the signed quote and exact budget/deadline are supplied.
