# EvidenceLab G2 — deterministic mutation lab

Completed2026-11-21 under owner approval for a separate corpus and tests only.
G3differential evaluation and G4local workflow are not approved or implemented.

## 1. Files changed and purpose

- `docs/EVIDENCELAB_G2_SPEC.md`: predeclared semantics, valid representations,
  exact edits and independently reasoned snapshot/temporal outcomes.
- `mutation_corpus.py`: deterministic synthetic fixture materialization using
  manual ABI word layout and literal recipe labels, no candidate oracle.
- `mutation_manifest.py`: exact manifest schema/coverage, spec/checksum binding,
  exclusive freeze creation and refusal to overwrite existing corpus files.
- `fixtures/evidencelab/g2-v1/corpus.json` and `corpus.sha256`: separate frozen
  corpus, preserving the historical40scenario manifest and all model records.
- `tests/integration/test_mutation_lab.py`:62case assertions plus15independent
  golden-byte, integrity, coverage, deterministic regeneration and format checks.
- New G2JUnit, freeze, summary and per-case artifacts in `artifacts/evidencelab`;
  STATUS/AGENTS/PLANS/README updated for actual phase state.

No G1candidate implementation, historical schema, reviewed allowlist, SDK,
wallet, escrow or settlement behavior changed. No new CLI/API/contract.

## 2. Freeze sequence and independent review

1. Draft semantics and62case recipes authored before generating/scoring data.
2. Independent G2reviewer checked the final spec and loader; early draft/loader
   discrepancies were resolved before freezing, not adjusted to observed results.
3. `g2-spec-freeze.json` recorded approved spec SHA256 before generation/execution:
   `ab65a8334084bed433dad08b2a2dffe5eb1fa0e7ea295cc6b91865c60e9ac549`.
4. Materialized and exclusively froze corpus SHA256:
   `dbf197d8c86274c3d0855db0ffa9c766e448292aea72b4c0763afc44d144f6c3`.
5. Reviewer compared every actual mutation/label to the frozen spec and manually
   decoded the golden job ABI words before candidate execution.
6. Only then ran the G2tests and retained expected/actual per-case results.

The initially assigned testing/QA specialists hit usage limits. Lead completed
G2implementation/spec/tests; the available evidence specialist was reassigned
to read-only G2QA and implemented **no G2component**. That reviewer authored the
earlier G1envelope, not the G2generator/loader/tests under review. No claim of an
independent new reviewer rebuilding the whole product or a blind experiment.

Review verified actual corpus bytes/checksum, complete recipe/label conformance,
manual golden decoding and no candidate/history imports. QA suggested direct
golden word/selector assertions; lead added two before final regression. AST
guards support source review; they are not a formal independence proof.

## 3. Tests executed and evidence

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mutation_lab.py -q --junitxml=artifacts/evidencelab/g2-focused-tests.xml
.\.venv\Scripts\python.exe -m pytest -q --junitxml=artifacts/evidencelab/g2-tests.xml
```

- Focused: **77passed**,1.89seconds.
- Full: **453passed,0failed/errors/skipped**,14.43seconds.
- One existing websockets.legacy dependency deprecation warning.
- Initial451test full run preserved as `g2-initial-tests.xml`, before adding the
  two QA-suggested golden-byte checks; final453run supersedes that coverage.
-62of62frozen cases matched all five specified outcomes. All14valid controls
  remained VALID_AT_SNAPSHOT; historical controls require revalidation.
- Per-case expected/actual labels and diagnostic reasons:
  `artifacts/evidencelab/g2-case-results.json`.
- Digests, counts, fullsuite results and limits: `g2-summary.json`.

Network is disabled around case assessment. No model/transaction calls; no live
RPC evidence was collected. Existing G1candidate, historical fixture and final
paired-model summary hashes were checked unchanged against G1artifacts.

## 4. Coverage and honest differences from baseline

62cases =31recipes ×2predicates:14valid controls and48mutations. Covers wrong
chain/target, ABI/function/selector, unreviewed proxy/runtime, block references,
stale/inconsistent timestamps, unfinalized/noncanonical flags, recorded conflicts,
unavailable/pruned/missing/malformed return data, incorrect allowance/status,
raw numeric scaling, unsupported threshold/numeric representations, wrong call
arguments and historical valid/invalid distinctions. Valid controls include
address/hash/byte-case equivalence, JSONlayout and freshness boundaries.

This adds frozen adversarial regression coverage and reproducible inputs. It
does **not** show greater correctness than the strong deterministic baseline.
No baseline, timing, integration effort or independent reproduction comparison
has run. Shared G1controls cannot be credited as new G2product value.

## 5. Security and compatibility limits

- Inputs and observations are SIMULATED_READ; provider flags/transcripts are not
  authenticated. No claim of chain truth, production safety or live attack testing.
- Conflicting-evidence cases toggle a recorded flag; no independent multi-RPC
  conflict acquisition/detection is implemented by this phase.
- Scaling means an erroneous raw value under equality semantics. Threshold
  operators are explicitly unsupported, not implemented threshold arithmetic.
- The token's proxy mutation tests unexpected identity metadata, not proof that
  the allowlisted token has a real proxy. No deployment state is altered.
- Local checksums bind content consistency; a writer can replace files and hashes.
- Current analysis authorization is absent in all cases; no case grants execution.
- G1canonical-byte policy is unchanged. New semantic/valid-format scope needs
  review; do not silently relax strict parsing or edit labels to fit failures.

Old callback deadline/recovery-accounting findings remain deferred. API budget
unchanged: historical$1.10conservative reservations of$2, invoice unknown.

## 6. Remaining uncertainties

No differentiated utility, lower development/review effort or independent
reproduction advantage established. The deterministic corpus is authored with
knowledge of the existing specification, not a blind held-out test. Passing all
cases is functional conformance, not generalization or product-market evidence.

## 7. Recommendation

**GO for owner review of G3**, solely to test differentiation against a strong
simple baseline. Product value remains **INCONCLUSIVE**; the original refusal-
recovery no-go and negative historical responses remain unchanged.

## 8. Exact next approval

Approve G3only: define/freeze fair protocol, scoring, effect-size thresholds and
effort/reproduction tasks before execution; implement an independent simple
baseline with identical information/scope/semantics; run deterministic differential
evaluation and report all disagreements and overhead. No advantage may be
attributed to shared checks or extra candidate-only evidence. No G4CLI, hosted
service, registry, paid model call, wallet action or deployment is implied.

Stop here until that approval. If no useful advantage is established, recommend
integration into existing agent/evaluator tooling rather than standalone expansion.
