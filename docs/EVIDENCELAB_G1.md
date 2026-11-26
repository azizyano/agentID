# EvidenceLab G1 — versioned validity envelope

Owner approved G1 envelope/types/compatibility/tests. This phase is separate
from the old experiment's protocol1 and its no-go result. No G2 scored mutation
corpus, G3 differential run or G4 CLI/workflow is implemented in G1.

## Format and boundaries

`evidence_envelope.py` defines the distinct namespace
`kind=veriabstain.evidence_envelope`, `envelope_version=1`. Historical evidence,
receipts and model requests retain their original schemas and data. Unknown
fields and loose boolean/integer substitutions are rejected.

| Record | Required meaning |
| --- | --- |
| claim | Supported predicate, chain, exact target/arguments, pinned block number/hash, asserted raw value/status |
| observation | Block and observation timestamps, freshness policy bounds, recorded finality/canonicality/ABI flags, finite errors/conflicts, source alias, assurance and historical-state capability |
| identity | Reviewed target/runtime, pinset/source revision, proxy implementation and its runtime where applicable |
| decoding | Exact function signature/selector, function-ABI SHA256, SDK revision, canonical codec identifier, calldata and return bytes |
| reproduction | eth_call, chain/target, number/hash-pinned block context and exact calldata |

The ABI digest is over the canonical JSON **function entry**, not the full ABI
file. The codec identifier specifies canonical ABI decode/re-encode equality;
trailing or noncanonical bytes are not silently normalized. SHA256/Keccak and
version/revision labels establish local consistency, not source authenticity.
The source revision in the reviewed identity refers to the existing pinset's
review reference. The earlier executable-runtime build comparison established
commerce correspondence; it did not prove test-U was built from that commit.

Scope remains the existing reviewed chain97 test-U allowance and commerce job
status. Semantic scope is raw uint256 equality or named job-status equality.
There are no new units, decimals, threshold operators, contracts or chains.
The SDK and old reader/validator are not modified. No model, signing, wallet,
network or submission operation is performed by envelope assessment.

## Snapshot and current use are distinct

`assess_envelope` revalidates the strict structure and compares its stored
identity/decoding information against reviewed definitions. It reconstructs
calldata, decodes recorded return bytes, requires canonical encoding and binds
the raw getJob ID/status where applicable.

- `VALID_AT_SNAPSHOT`: matching claim under supported recorded observations.
- `INVALID_AT_SNAPSHOT`: supported decoded observation contradicts the claim.
- `UNSUPPORTED_OR_INCONCLUSIVE`: missing/malformed context, unsupported
  identity/semantics, failed checks, unavailability or conflicts.

Temporal status is independently `CURRENT`, `REVALIDATION_REQUIRED` or `UNKNOWN`.
Evidence must have been fresh at observation (block age at most120seconds).
A previously supported snapshot can remain valid or invalid historically when
its current freshness is exhausted; it then requires revalidation. Failed or
pruned/missing/unknown provider-state capability is inconclusive, not evidence
that a claim is false. G1 does not contact an archive provider or classify live
RPC errors; capabilities here are recorded inputs only.

Authorization is separately reported as CURRENTLY_AUTHORIZED, BLOCKED or
NOT_PROVIDED. An expired current authorization does not rewrite historical facts.
`current_use_allowed` means a matching, locally current analysis with matching
current analysis authorization **under the recorded assurance**, not a fresh
online validation, permission to spend or permission to submit. In particular,
SIMULATED_READ remains simulated even with a current analysis authorization.
`execution_authorized` always remains false and authenticity NOT_ESTABLISHED.

All flags and raw transcripts are supplied records. A malicious author/provider
can fabricate a self-consistent package; this is offline assessment, not proof of
chain state or independent finality authentication. RPC observations remain
RPC_FINALIZED_READ. Keep packages private; raw call results can contain public
on-chain job descriptions. Do not attach confidential prompts, credential URLs,
wallet material or sessions. Source IDs are stable aliases, not endpoints.

## Compatibility strategy

`envelope_compat.py` defines `veriabstain.legacy_import`, compatibility version
`1.0`, with separate source formats for old evidence, file receipts and callback
receipts. It copies canonical JSON content and retains its digest without
mutating the original. Legacy metadata is a private historical record, not a
redacted public receipt or a complete new envelope.

`assess_legacy_import` reports missing reproduction context or historical receipt
only. It never fabricates block timestamp, raw return bytes, pin identities or
an authenticated verdict. Callback-specific fields and reasons are not confused
with the file inspector's format.

`build_envelope_from_legacy` requires explicit additional observation, identity,
decoding and reproduction inputs. It preserves the old claim and refuses changes
to source, observed-at, finality/canonicality/ABI flags, conflicts, error presence
or assurance. A malformed/unsupported result still requires envelope assessment;
constructing a typed object is not acceptance. Receipts cannot reconstruct an
evidence envelope.

**Retain the legacy wrapper alongside the derived envelope.** The new envelope
alone does not embed the original source digest or replace the historical record.
The wrapper is content-bound, not signed, and cannot authenticate the legacy
source. No historical file is migrated in place.

## Tests, review and next gate

G1 checks use independent fixed raw ABI examples for allowance and job state,
not scored G2 mutation/evaluation data. These establish implementation behavior,
not differentiated utility. On2026-11-21:

- Focused G1 command: `pytest tests/integration/test_evidence_envelope.py
  tests/integration/test_envelope_compat.py -q
  --junitxml=artifacts/evidencelab/g1-focused-tests.xml`: **63passed**,1.58seconds.
- Full command: `pytest -q --junitxml=artifacts/evidencelab/g1-tests.xml`:
  **376passed,0failed/errors/skipped**,13.44seconds; one existing dependency warning.
- Independent QA reran63checks and ten additional transcript/context probes;
  no remaining G1 blocker. QA implemented no component under review.
- The independently discovered nested Pydantic/model_construct bypass was fixed:
  new assessment reconstructs bounded primitive input trees, revalidates nested
  models and authorization, and suppresses serializer warnings. Eleven regression
  checks cover the bypass family. Pre-QA green365test evidence is preserved as
  `g1-preqa-tests.xml`; it lacked that coverage and is superseded by the376run.
- Original frozen manifest and historical final-comparison summary SHA256 values
  remain unchanged. No paid call, live RPC, wallet operation or submission ran.

Generated envelope/assessment/legacy-import JSON schemas and an offline summary
are under `artifacts/evidencelab/g1-*.json`. The example
`examples/evidencelab/envelope-v1-allowance.json` is explicitly simulated, not a
real observed block or scored mutation fixture. Keep the old313test baseline and
G0 artifact as historical evidence, not overwritten test history.

File ownership: evidence engineer implemented only evidence_envelope.py; testing
engineer independently authored its G1tests; lead implemented envelope_compat.py,
its tests, example/schema exports and documentation. QA reviewed read-only.

Compared with the baseline, this phase adds explicit reproduction/identity and
temporal/compatibility structures. It does not demonstrate improved detection,
lower effort or independent reproduction success. Those remain INCONCLUSIVE.
Recommendation: **GO to owner review of bounded G2**, not a product-success gate.

Existing callback deadline and old malformed-retry accounting findings are
unchanged. The optional deadline fix was not included in the approved G1 scope.

Before G2, owner must approve the separately versioned mutation-lab scope and
freeze semantic definitions, valid representation rules and independent expected
labels. G3 differential scoring/thresholds and G4 local workflow require later
approvals. No extra correctness or reviewer-effort advantage has yet been
measured against the strong baseline.
