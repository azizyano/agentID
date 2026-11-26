# EvidenceLab G3 — differential result

Completed2026-11-21. Decision: **NO-GO for standalone expansion on current
evidence.** No demonstrated correctness or runtime advantage. Integration/review
effort advantage remains unmeasured, not disproven or assumed. Recommend reusing
the useful components in existing agent/evaluator infrastructure.

## 1. Files changed and why

- `EVIDENCELAB_G3_PROTOCOL.md`: independently reviewed predeclared fairness,
  correctness/runtime thresholds and effort/reproduction tasks; frozen before
  baseline implementation or scored execution.
- `deterministic_baseline.py`: independent bounded plain-JSON checker, using
  reviewed constants and upstream ABI/eth_abi, no candidate/legacy/oracle imports.
- `differential.py`: equal-input scoring, content-nonmutation checks, scheduled
  assessment-only timings and complete result/source metadata. Internal G3test
  harness only, not a new G4user command.
- `test_differential.py`: baseline conformance and strict metric/harness guards.
- G3freeze/run/test/review artifacts, current status and phase documentation.

G1candidate, G2corpus, historical model results, reviewed target scope and SDK
signer/escrow/settlement remain unchanged. No optimization or rerun after viewing
the first benchmark result.

## 2. Frozen protocol and independent review

Protocol SHA256:
`973dfb8f12740fc734bbf49af701562410bc39822d0cd19bcdeb5b494e2c03ec`.
Corpus SHA256:
`dbf197d8c86274c3d0855db0ffa9c766e448292aea72b4c0763afc44d144f6c3`.

`g3-protocol-freeze.json` predates baseline implementation/execution. Independent
read-only QA reviewed the baseline for complete/equal checks and no candidate
oracle, then the runner before execution. QA caught a gate bug: snapshot-only
control counts could miss other control-outcome regressions. Fixed before first
run with full-five-field control gating, explicit unauthorized-use gating and
exact-type equality (False must not equal integer0). Regression checks added;
no observed outcomes or thresholds were changed.

Final reviewed runner SHA256:
`c9fc1228a13520adb132f534f3180686a0fa8b404ca48c455b66ff27fec4bddd`.
Baseline SHA256:
`7e003c3476d1f324dc48e69bf884de26050bb2651b53fd87efc736883e122887`.
Actual run configuration records nine local source hashes and package versions;
this is not full transitive source attestation.

First scored execution used the existing local interpreter with a here-string
calling `run_differential(Path('artifacts/evidencelab/g3-v1'))` from
`veriabstain_eval.differential`. It exited0. The output directory is exclusive;
the preserved run was not overwritten or rerun after inspection.

Root implemented baseline/harness/tests. Separate QA implemented no G3component
under review, although that reviewer authored the earlier G1candidate. This is
not a blind participant study or a clean-room product reconstruction.

## 3. Correctness and incomplete-evidence results

| Measure | Strong baseline | EvidenceLab candidate |
| --- | ---: | ---: |
| Exact five-field matches | 62/62 | 62/62 |
| Valid controls rejected | 0/14 | 0/14 |
| Full control-outcome errors | 0 | 0 |
| Invalid/incomplete evidence falsely accepted | 0 | 0 |
| Temporal/authorization errors | 0 | 0 |
| Unauthorized current-use/execution grants | 0 | 0 |

Both classified14valid snapshots,5supported incorrect snapshots and43unsupported/
inconclusive cases identically. No candidate-only correct case or baseline-only
correct case. Shared protection is not candidate differentiation.

Inputs are the known synthetic G2set, not held-out model evidence. Both receive
the same parsed plain JSON, frozen now and no authorization; neither receives
expected labels. These results do not establish general correctness or safety.

## 4. Local runtime results

| Assessment time | Baseline | Candidate | Candidate / baseline |
| --- | ---: | ---: | ---: |
| Median | 166.35µs | 1916.75µs | 11.52× |
| Nearest-rank p95 | 688.2µs | 12668.3µs | 18.41× |

One untimed correctness pass precedes2warm-up rounds, then20measured rounds for
every62cases/system. Fixed seed20261121, shuffled cases and seeded system-first
order;2480measured samples,1240per system. Content digests verify input preservation
around every assessment. Deep copies, parsing, common normalization and digest
work are outside both timers. Assessment's own validation/return construction is
inside timing. Baseline caches immutable ABI metadata; unchanged candidate uses
its existing upstream loader/Web3 path. This is a disclosed strong-baseline
optimization, not an unequal-evidence condition.

Results are local as-implemented overhead, not production throughput, RPC latency,
gas, financial cost or proof that future implementations cannot be optimized.
The frozen20%median+p95 candidate-improvement threshold was not met. No tuning or
benchmark repetition was used to manufacture a better result.

## 5. Tests and independent functional replay

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_differential.py -q --junitxml=artifacts/evidencelab/g3-focused-tests.xml
.\.venv\Scripts\python.exe -m pytest -q --junitxml=artifacts/evidencelab/g3-tests.xml
```

Focused73passed in1.87seconds. Full **526passed,0failed/errors/skipped**,20.82seconds;
one existing websockets.legacy warning. Regression tests are not another timed
benchmark or a rewrite of the first scored result.

Independent QA audited all case counts, source/protocol/corpus hashes, positive
timings and exact seeded scheduling, and recomputed median/p95. No mismatch.
Then, in a new isolated Python interpreter using the existing virtual environment,
QA replayed matchedjob, prunedjob and changed-calldata allowance packages:

| Raw package | Both reproduced |
| --- | --- |
| job status/matched | VALID_AT_SNAPSHOT / CURRENT |
| job status/pruned state | UNSUPPORTED_OR_INCONCLUSIVE / UNKNOWN |
| allowance/call argument mismatch | UNSUPPORTED_OR_INCONCLUSIVE / CURRENT |

No expected labels were passed to the checkers. All returned NOT_PROVIDED
authorization, false current-use and false execution. Command form: PowerShell
here-string piped to `.\.venv\Scripts\python.exe -I -`, explicit raw JSON+now and
network-disabled guard. Dependencies available: Python3.12.4, Pydantic2.14.4,
web3 7.16.0, eth-abi6.0.0, bnbagent0.5.1. This was **not** a clean dependency
rebuild, an unfamiliar participant study or a candidate reproduction advantage;
both succeeded. No matched developer/task timing observations were available,
so integration/review effort advantage remains **NOT_MEASURED**.

## 6. Evidence locations and limits

- `artifacts/evidencelab/g3-protocol-freeze.json`.
- `g3-v1/run-config.json`: exact protocol/corpus/source versions, setup and limits.
- `g3-v1/case-results.json`: every expected/actual outcome and mismatched field.
- `g3-v1/timings.json`: every measured sample.
- `g3-v1/summary.json`: original scored recommendation and aggregate statistics.
- `g3-review.json`, `g3-phase-summary.json`, focused/full JUnit artifacts.

SIMULATED_READ throughout; no authenticated chain data, live RPC acquisition,
multi-provider conflict detection, threshold arithmetic or real asset attacks.
Checksums do not authenticate authorship. No model/paid/wallet/transaction calls,
deployment or credentials. Historical API reservations unchanged$1.10of$2;
provider invoice remains unknown. Optional callback deadline fix still deferred.

## 7. Recommendation and remaining uncertainties

Correctness: no measured candidate advantage on the known62case set.
Runtime: no measured candidate advantage; candidate slower in this run.
Effort/review: advantage INCONCLUSIVE/NOT_MEASURED, not a basis for GO.

The mission's continuation criterion is not satisfied. **NO-GO for expanding a
standalone EvidenceLab product on this evidence.** This does not prove no value
could exist in another task, model, dataset or independently measured review
workflow. Preserve the negative result and reuse limited collectors, validation,
versioned transcript structures and regression cases where they help existing
agent/evaluator tools. Do not claim unique value from shared controls.

## 8. Owner decision before further work

G4has not started and is not automatically recommended. Owner must explicitly
choose a bounded integration target or a separately justified new experiment;
specify expected benefit and evaluation before expanding scope. Any later G4local
reproduction work also requires approval and cannot imply a hosted service,
registry, production recovery, transaction or deployment. Stop here for review.
