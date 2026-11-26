# G1 pre-registered experiment plan

Status: G1a fixtures and G1b offline comparison adapters implemented. The frozen [manifest](../fixtures/g1a.json) still has 40 cases. [G1a results](../artifacts/g1a/summary.json) show 40/40 expected outcomes. The [comparison protocol](WORKER_PROTOCOL.md) exports 200 requests across five arms; all currently await model responses. No real AI baseline has run; behavioral proof is BLOCKED.

## Dataset and comparison

Freeze a versioned manifest before running workers: 2 predicates (ERC-20 allowance and supported ERC-8183 job state) x 10 conditions x 2 parameter variants = **40 paired scenarios**. Fix ground truth, objective expected output, original authorization, pinned snapshot, tool payload, and operation ID for each. Publish all scenario IDs and failures, not selected screenshots.

Conditions: false warning; genuine warning; stale evidence; mismatched chain; proxy/ABI mismatch; provider outage; unreadable evidence; contradictory sources; independent authorization denial; duplicate/ambiguous submission. Parameter variants must use distinct values/targets, not duplicate labels. Record validity and factual correctness separately: reporting a genuine warning can still complete an authorized analysis task correctly.

- A: ordinary worker with the controlled tool response.
- B: same worker with verify-before-refusal instructions.
- C: same worker with correct instructions and a straightforward trusted contract/RPC read.
- D: same worker with typed evidence, explicit decision assessment, unchanged authorization, and one journaled recovery attempt.

C and D receive equivalent authoritative facts, snapshot access, and policy information. Record differences in retries, context, and tool/token budgets; add a C-with-equal-retry-budget control before attributing benefit to VeriAbstain. Use the same model/version, task prompt, and decoding settings. Capture observable structured decisions, not private chain-of-thought.

## Staged execution

1. Implement the manifest and deterministic runner in this repository. Inject contract reads at the SDK client boundary while invoking real `funded_job_watcher` / `verify_job` logic. Use valid signed-quote fixtures with ephemeral unfunded test identities. Intercept all submission I/O; label this stage FIXTURE_ONLY.
2. Run upstream watcher/job-ops/schema tests to establish compatibility. Install the SDK from its immutable revision; resolve and retain the environment lock before integration.
3. Establish an isolated local EVM funded-job environment using separately pinned compatible official commerce/router/policy deployment artifacts. Source/artifact availability is unresolved; do not pretend mocked RPC responses establish real integration. No production funding or transactions.
4. Implement actual worker A/B/C/D adapters and run the same frozen manifest. Without an authorized real model runtime, behavioral proof remains BLOCKED. Check runtime availability without printing credentials; no paid calls without authorization.
5. For real-model evaluation, plan three repetitions of each of 40 scenarios per arm (480 decisions), with paired randomized order and every raw outcome retained. Review the resulting cost estimate before any paid run. Deterministic fixtures are separate from these repetitions.
6. Measure correct authorized completions, factual error/refusal rate, unauthorized/duplicate effects, stale decisions, latency, actual tokens/model cost, and actual local-chain gas. Unknown cost stays unknown; local gas is not mainnet spending.

## Execution record

The reference classifier consumes a typed claim and simulated read, not the condition label or expected answer. It is an experiment oracle, not an AI worker. The runner calls the real upstream discovery/watcher/verifier with ephemeral signed quotes; only contract I/O is injected. Proposed analysis submissions are recorded in memory. Production submission, worker recovery, and a durable journal are not implemented.

The separate comparison harness now persists request/response slots in SQLite. This experiment ledger limits reconsideration and detects changed authorization or conflicting replays; it is not a production effect journal. A real-model refusal must name a matching typed factual basis before D can request reconsideration. C_RETRY uses the same two-call ceiling to control for retry budget. Every arm shares objective deliverable and authorization checks.

Local results: 140 current project tests and all 40 frozen scenarios passed after team integration; the earlier G1a run passed 149 selected SDK tests. See [runbook](RUNNING.md) and [current artifacts](../artifacts/part1/). Prior evidence remains in the G1a/G1b artifact directories.

## Upstream compatibility setup

After local execution prerequisites and Python 3.12 are confirmed, commands for PowerShell:

```powershell
git clone https://github.com/bnb-chain/bnbagent-sdk.git .research/bnbagent-sdk
git -C .research/bnbagent-sdk checkout --detach 260e16196931780d0370bd3a9d9b67ece744bb9d
py -3.12 -m venv .venv
uv pip sync requirements-test.lock --python .venv/Scripts/python.exe --cache-dir .research/uv-cache
Push-Location .research/bnbagent-sdk/python
try {
    & ..\..\..\.venv\Scripts\python.exe -m pytest tests/test_funded_watcher_verification.py tests/test_erc8183_job_ops.py tests/test_erc8183_schema.py
} finally {
    Pop-Location
}
```

These are upstream compatibility tests. The lock includes the SDK Git revision and resolved transitive runtime/test versions. Isolated package-build dependencies are not locked; bit-for-bit builds are not claimed.

## Decision rule

GO requires a reproducible nontrivial C failure that D fixes, plus zero observed unauthorized or duplicate effects across all conditions. Retest the candidate failure with equal-budget C and altered parameter variants. Report paired counts, variability, raw logs, prompts, model version, environment, and limitations. Otherwise NO-GO or an explicitly narrower pivot. Owner review precedes G2.
