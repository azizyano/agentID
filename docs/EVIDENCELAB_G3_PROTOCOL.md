# EvidenceLab G3 differential protocol v1.0

Freeze this exact specification after independent review and BEFORE baseline
implementation or differential execution. No edits after results; corrections
require a recorded new version with prior results preserved.

## Hypothesis, inputs and fairness

Question: does the G1envelope utility improve correctness, runtime or independently
observed integration/review/reproduction effort over a strong simple deterministic
checker with the same information and reviewed scope?

Use the already frozen G2v1.0 corpus:62cases,14valid controls,48mutations,
SHA256dbf197d8c86274c3d0855db0ffa9c766e448292aea72b4c0763afc44d144f6c3.
Its independently specified labels and semantics remain fixed. This is a known
synthetic regression/differential set, NOT blind held-out evidence. No historical
LLM replies, liveRPC data, transactions or new corpus tuning.

Both systems receive the same parsed plain JSON package, exact now and no
authorization for scored cases. Parse with the shared strict JSON importer
outside timed sections. Give each an independent deep copy outside timing;
check inputs remain unchanged. Neither system receives expected labels.

Both must preserve exact chain97allowlists, reviewed runtime/proxy/ABI identity,
source/finality/freshness/error/conflict semantics, rawuint/status equality,
canonical ABI encoding, case normalization and recorded temporal distinctions.
Unsupported/pruned evidence is inconclusive, not a false-claim finding.

Baseline implementation must be separate and not import candidate envelope
classes, assessment, helpers, legacy grader or corpus oracle. It may use Python
utilities, pinned upstream SDK ABI functions and independent eth_abi encoding/
decoding. ABI/review metadata and supported definitions are shared facts, not
candidate verdicts. Hand-written bounded strict primitive/field checks are
acceptable; no omitted control is credited as a candidate advantage.

Independent reviewer checks baseline rules/inputs and exact label semantics
before execution. Defects found later must be recorded; no silent weakening or
repair to manufacture an advantage. G1candidate and frozen G2data remain unchanged.

## Correctness scoring and success thresholds

For every case compare the same five fields: snapshot_status, temporal_status,
authorization_status, current_use_allowed and execution_authorized. Exact full
match is one correct case; report mismatched fields, expected/actual and diagnostic
reason separately. Include every case, not just valid/parseable ones.

Report per-system counts, all disagreements, V/I/U confusion counts, false rejection
on14valid controls, incorrect acceptance of invalid/incomplete evidence and
temporal/auth errors. Historical valid controls are valid snapshots, not current
execution permission. Blanket rejection cannot pass this scoring.

Descriptive correctness improvement requires at least2net additional correct
cases of62, zero valid-control regressions and zero introduced false acceptance
or execution grants. These are preregistered engineering thresholds, not a
statistical population-level significance test. Shared controls do not count as
new functionality; inspect any apparent win for baseline bugs or unequal facts.

## Runtime measurement

Offline only, same interpreter/machine/process, network disabled, no tools/model
operations. Use perf_counter_ns around assessment only; common parse/copy/digest
checks are outside timing. Each system performs its own schema/semantic validation.
Per-system setup may cache immutable ABI definitions; disclose caching differences.

-2complete warm-up rounds, then20measured rounds over every62cases.
-Fixed scheduler seed20261121; shuffle case order each round and alternate which
  system runs first through seeded random coin flips.
-Record all per-case nanosecond observations, not only aggregate averages.
-Report pooled and per-predicate median/p95 via sorted nearest-rank p95; report
  absolute microseconds and candidate/baseline ratios, not RPC or gas estimates.
-Candidate runtime advantage requires at least20%lower median AND p95, with no
  correctness/control/safety regression. Equal correctness alone is not an advantage.

Do not tune thresholds, repetitions, output schema or implementation after viewing
timings without retaining and separately versioning the original run. Timing is
local descriptive overhead, not production throughput or general cost evidence.

## Integration effort and reviewer reproduction

Predefined integration task: wire a supplied prepared allowance package into a
keyless local analysis callback and expose snapshot/current/unsupported results
without expanding authorization. Record actual developer edits, elapsed active
time, assistance and review corrections for matched candidate/baseline tasks.
Use separate participants or counterbalanced assignments before claiming lower
effort; prior project investment and source line counts are not such measurements.

Predefined reviewer task: use the published format and same frozen raw package
for matchedjob, pruned-state and changed-calldata cases, reproduce both systems'
five outcomes in a new interpreter without hidden expected labels/process state.
Record commands, dependency availability, missing inputs and disagreements.
An existing environment is not a clean dependency rebuild. Recorded RPC bytes
remain unauthenticated; no online historical-state capability claim.

A meaningful effort/reproduction advantage would require at least25%lower active
time or fewer blocking reproduction failures over at least3matched independently
observed tasks/participants, with no weaker checks. If matched participants/time
logs are unavailable, mark effort/time advantage NOT_MEASURED and do not award it.
Limited reviewer functional replay may be reported without a speed/effort claim.

## Execution evidence and decision

Before execution retain protocol/corpus/candidate/baseline/source hashes and
review approval. Persist every per-case result and timing, package versions,
interpreter/platform (no credentials/environment dump), seed and thresholds.
No paid model calls, wallet operations or public receipts.

GO for further standalone development only if a useful correctness, runtime or
independently measured effort/reproduction advantage survives fair baseline
review. Otherwise report NO-GO for standalone expansion on this evidence and
recommend integrating reusable pieces into existing agent/evaluator tools.
Unmeasured effort is INCONCLUSIVE, never an inferred benefit. No global claim
that value is impossible elsewhere. Preserve original refusal-recovery no-go.

G4CLI/reproduction product workflow requires later owner approval. No hosted
service, registry, deployment, paid call, transaction or optional callbackdeadline
fix is authorized by G3.
