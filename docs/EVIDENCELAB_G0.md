# EvidenceLab G0 — repository inspection and baseline

Date:2026-11-20. Scope: the owner's new EvidenceLab mission, **G0 only**.
No feature implementation, deployment, wallet operation or model call authorized
or performed in this phase. Existing negative findings remain unchanged.

## Decision

**INCONCLUSIVE on differentiated EvidenceLab value.** The existing utility is
already a strong deterministic checker. A new name or schema cannot establish
additional correctness. A bounded G1 envelope implementation is worth owner
review primarily for reproduction and review effort, not a demonstrated
correctness advantage. G1 requires explicit approval; G2–G4 are not approved.

The original refusal-recovery G1 no-go remains. EvidenceLab has its own new
G0–G4 sequence; these labels must not silently replace the historical gates.

## 1. Files and verification performed

New documentation: this report and EVIDENCELAB_BASELINE.md. STATUS.md and
AGENTS.md record the new mission boundary. PLANS.md links the new gated track.
New test artifact: `artifacts/evidencelab/g0-tests.xml`. Existing implementation,
tests, prompts, manifests, model responses and budget journals were not edited.

Lead integrated read-only source/artifact reports from separate evidence,
historical-evaluation and independent QA specialists. No specialist implemented
a component. Explicit read-only ownership avoided shared-schema edits. The
repository is an unborn/uncommitted working tree with existing untracked files;
no branch, merge or commit was created or claimed.

Actual command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=artifacts/evidencelab/g0-tests.xml
```

Result: **313passed,0failed,0errors,0skipped**,8.96seconds reported by pytest,
one existing websockets.legacy dependency deprecation warning. JUnit suite time
is8.886seconds. This verifies the current test baseline, not correctness outside
its coverage or product utility. No live RPC read was needed for G0.

Source checkout revisions verified by `git rev-parse HEAD`:

- BNB SDK: `260e16196931780d0370bd3a9d9b67ece744bb9d`.
- apex-contracts: `f6a3c4ff337158a8a66281c565f3f1562e1287b7`.

## 2. Actual dependency and reuse map

Paths below are relative to this repository; line numbers identify inspected
entry points, not promised stable API locations.

| Component | Actual implementation | Dependencies / reuse |
| --- | --- | --- |
| Chain evidence | `packages/evaluation/veriabstain_eval/chain_evidence.py:16` | web3, upstream `load_abi`, Scope/Evidence, reviewed deployment pins |
| Target scope/pins | `chain_evidence.py:8`; `testnet_deployment.py:13` | chain97 test-U runtime; commerce proxy and EIP1967 implementation/code hash |
| Typed validation | `deliverables.py:13`,`:47`,`:71`,`:87` | strict Pydantic schemas, exact raw values, authorization, evidence freshness |
| Practical check | `check_analysis.py:14` | same collector and validator; candidate block independently checked |
| Local receipts | `check_analysis.py:40`; `receipt_inspection.py:53` | canonical content digest, private atomic storage, shape/digest inspection |
| Callback/journal | `application_callback.py:14`,`:39`,`:59` | SDK verify_job, approved job binding, SQLite reservation and cached historical result |
| Old evaluation | `dataset.py`, `runner.py`, `comparison.py:27`, `comparison_state.py` | frozen40cases, actual SDK verification with simulated chain I/O, A/B/C/C_RETRY/D |
| Response import | `workers.py:75` | ID/digest-bound recorded responses; no model attestation |
| Paid transport controls | `deepseek_runtime.py:34`,`:93`; `tools/run_deepseek_batch.py` | shared$2reservation journal, hidden owner key input, no ambiguous-call retry |
| Local entry | `tools/veriabstain.py` | doctor/demo/check/receipts; no paid runner or transaction command |

Reuse the existing collector/pins, strict JSON handling, atomic storage pattern,
SDK callback boundary and original test protections. Keep the old evaluator and
schemas readable unchanged. Prefer a separate EvidenceLab namespace/versioned
format rather than rewriting historical `Evidence` or protocol1 in place.

Upstream `.research/bnbagent-sdk/python/bnbagent/erc8183/job_ops.py` exposes
`submit_result` at351, `get_job` at445, `verify_job` at643 and
`funded_job_watcher` at1128. The watcher verifies before callbacks and expects
SDK fields `jobId`/`expiredAt`. Preserve these interfaces and all signer, quote,
escrow, submission and settlement handling. EvidenceLab does not need to add a
signer or change any of those upstream methods.

## 3. Verified historical findings

- `fixtures/g1a.json`:40cases,10conditions×2predicates×2variants; SHA256
  `263a482d06e2eef62fbdbc33b7a91d5c4c3df29f71a9201a1f987d8f0a7cb389`,
  verified against the frozen sidecar and current loader/tests.
- `artifacts/private/deepseek/paired-final-summary.json` and current
  `artifacts/g1b/results.jsonl`:16matched cases per C/C_RETRY/D; accepted1/1/1,
  same allowance false-warning case; zero D-only accepted completions.
- Private DeepSeek journal/export:55COMPLETE rows/55unique replies;
 46,704input and5,555output tokens, provider-reported; conservative$1.10reserved
  of$2. Invoice cost unknown. No key/credential was inspected.
- `artifacts/testnet/quote-attempt2/settlement-confirmed.json` records prior
  completed job1766 and1testU payout. It is historical RPC evidence, not a fresh
  G0 chain revalidation or proof of new callback behavior.
- `artifacts/testnet/source-verification.json` records executable-runtime match
  after known UUPS linking and metadata exclusion, but full-runtime mismatch.
 37SDK function shapes and19event layouts agree. Do not call this unqualified
  full source identity or independent authentication.

The old model experiment used simulated reads and provider-reported responses.
It is not a blind EvidenceLab experiment and must never be reused as one.

## 4. Strong baseline and current differences

The detailed proposed baseline is in EVIDENCELAB_BASELINE.md. Its core is the
**existing deterministic utility**: equal authorized scope, same reviewed
reader/ABI/runtime/proxy/finality/freshness rules, direct typed equality against
the same block and value, and explicit incomplete/unsupported outcomes.

Several requested failure checks already exist in reader and validator tests.
Provider-conflict comparison, scaling/threshold semantics and broad valid-format
normalization are not implemented. There is currently no demonstrated new EvidenceLab correctness
advantage over that baseline. Shared controls cannot be credited twice.

Possible differentiation to test, not assume: portable reproduction context,
explicit semantic versions, snapshot-vs-current result separation, meaningful
valid-format controls, or independently measured lower integration/review effort.

## 5. Independent QA findings and compatibility risks

1. **Reproduction gap, source-confirmed:** receipts retain record digests but not
   the original trusted inputs, raw call/result bytes, checked runtime identities
   or decoding recipe (`check_analysis.py:40`; `deliverables.py:131`). Offline
   CONTENT_CONSISTENT cannot reproduce the underlying predicate.
2. **Validity-model gap:** current reader rejects blocks older than120seconds;
   validator freshness ceiling is300seconds. No separate historically-valid /
   requires-current-revalidation outcome exists. Historical RPC pruning or
   missing-state capability is not classified. Existing rejection behavior must
   not silently change when a new envelope is introduced.
3. **Trust limits:** one provider can lie consistently. The collector sets
   `conflicting=false` without comparing independent sources; this means no
   conflict observed by the current mechanism, not corroboration. Offline
   validation trusts caller-supplied canonical/finality/ABI flags.
4. **Deadline defect, source-confirmed but not dynamically reproduced in G0:**
   callback checks deadline before collecting evidence, then invokes the worker
   without rechecking after collection (`application_callback.py:74–86`). A
   collector crossing the deadline can cause a worker/inference call after
   authorization expiry, although final validation rejects the output. Existing
  313tests do not cover that timing boundary. No asset-execution exploit claimed;
   no fix made in G0.
5. **Attempt-accounting defect, source/artifact-confirmed:**
   `comparison.py:58–59` updates recovery_attempts only after output parsing.
   Two recorded C_RETRY round1 replies were invalid, so displayed recovery count
   remains0 despite attempted reconsiderations. Preserve historical results;
   future accounting must distinguish attempted calls from parsed decisions.
6. **Upstream qualification:** SDK dispute-window lookup failure logs a warning
   and proceeds without that particular check (`job_ops.py:719–736`). Preserve
   upstream behavior and document it; do not claim every SDK check fails closed.
7. **Semantic gaps:** current allowance is exact raw uint256, not decimals or
   threshold claims. Address/hash case equivalence is handled; numeric strings
   are rejected. Scaling/threshold/alternative-format scoring needs an explicit
   new semantic specification and independently defined valid controls.
8. **Journal/storage limits:** callback reservation prevents repeat worker calls
   for the same bound job; errors require reconciliation. Caller owns worker
   runtime/cost bounds. Cached receipts are historical. Local hashes/journals are
   not authenticated against someone who can rewrite files.
9. **Receipt interoperability:** callback receipts add submission/cached fields
   and callback-specific reasons not accepted by the file receipt inspector's
   allowlist. These currently use different storage paths. Explicit future
   format adapters are needed; do not silently rewrite historical receipts.
10. **Test-oracle limit:** reader plumbing tests mock runtime hashes and derive
    an expected deliverable from returned evidence. This tests composition, not
    independently specified mutation detection. The new corpus needs external
    expected labels rather than either implementation as its oracle.

These are inspection findings, not implemented features or a complete security
audit. No unrelated skill-driven audit, live exploit or production investigation
was launched.

## 6. Remaining uncertainties and future evaluation

No measured improvement in correctness, development effort or independent
reproduction yet exists for EvidenceLab. Baseline APIs/scenarios/scoring need
freezing before the new differential run. Integration effort must be measured
with comparable tasks and assistance, not asserted from line counts or prior
work. New expected behavior must be independent of both implementations.

G1 should propose a separate versioned envelope containing supported predicate
semantics, exact call/decoding identity, reviewed code/proxy identities, pinned
block context, observation/freshness policy, source/assurance and privacy-safe
reproduction inputs. Its observed-snapshot assessment and need for current
revalidation should be separate; no offline truth/authenticity claim.

Before generating/executing the scored G2 corpus, freeze semantic definitions,
valid formats and independent expected-label rules. Freeze exact scenarios and
G3 protocol/thresholds before differential execution. G2/G3 must use a separate
versioned corpus/scoring document, valid controls and equal inputs for both
systems. Missing/pruned state is inconclusive, not an
invalid-claim verdict. G4 can later reproduce recorded inputs offline while
explicitly retaining provider trust, with optional online rechecks reporting
capability limitations. None of those phases begins during G0.

## 7. Exact next approval

Owner approval requested only for **EvidenceLab G1**:

- Separate versioned envelope types and explicit compatibility adapters/tests;
  no historical schema/data rewrites or allowlist expansion.
- Distinguish observed valid/invalid, historical-revalidation-needed and
  unsupported/inconclusive outcomes while preserving assurance labels.
- Record enough approved reproduction/semantic context to permit later review;
  no secret endpoints, prompts, credentials or wallet material.
- If explicitly included by owner, separately fix/test the callback's
  pre-worker deadline recheck. Preserve the old experiment outputs; any accounting
  correction must be additive/versioned, not a silent historical rewrite.

No G2mutation implementation, G3differential execution, G4workflow, paid model
calls, new transactions, deployment, dashboard or registry is authorized by
this recommendation. **Stop here until owner approval.**
