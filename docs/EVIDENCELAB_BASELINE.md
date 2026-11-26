# EvidenceLab strong deterministic baseline — G0 proposal

Status: proposed specification only; no baseline implementation or differential
run in G0. Freeze exact APIs, corpus and scoring before G3execution. Existing
negative experiments remain historical and cannot become blind new test data.

## Equal scope and information

Both candidates support only reviewed chain97 test-U allowance and commerce
job-status predicates, using the same allowlists, code/proxy review pins, ABI
semantics, current authorization and RPC-provider trust. No signer or chain write.

Share low-level evidence access/pins where appropriate. Give both the same
observation transcript/package and provider capabilities. An envelope must not
give only EvidenceLab extra facts unavailable to the baseline. Add small direct
baseline adapters when new semantics/formats are explicitly introduced, so it
does not lose merely because an equivalent encoding was withheld from it.

For envelope/verdict evaluation, a shared collector is fair, but a shared
reader's pin/proxy/finality checks cannot establish a new correctness advantage.
If evidence-acquisition correctness is under test, supply independently defined
raw RPC observation tapes to a separate baseline acquisition/check path. Neither
system's normalized values or quality flags may serve as the golden oracle.

## Simplest correct implementation

1. Strictly parse the independently approved task and candidate analysis; reject
   unsupported keys/types/predicates and scope/deadline violations.
2. Independently read the requested canonical finalized block under identical
   freshness, runtime/proxy/ABI and chain restrictions.
3. Decode allowance as raw uint256, or known commerce job status, using identical
   reviewed definitions. Do not infer decimals/thresholds from raw integers.
4. Compare normalized addresses/arguments, chain, exact block number/hash and
   typed value. A factual match never grants action permission.
5. Return valid-at-snapshot, invalid-at-snapshot or unsupported/inconclusive with
   explicit provider assurance. Distinguish lack of current revalidation from a
   factually incorrect historical claim. Same logical distinctions for both.

The current check_analysis/validate_deliverable utility largely embodies this
baseline. A future independent small baseline can reuse the collector while
keeping verdict logic independent from the candidate envelope implementation.
Do not implement expected labels by calling either system under test.

## Independently specified controls

The later frozen corpus should include wrong chain/target, unsupported ABI,
unreviewed implementation, stale/inconsistent snapshot, incorrect job assertion,
unavailable/conflicting evidence, scaling/threshold errors only under approved
semantics, and valid alternative representations. Include correct unchanged
controls and valid normalization controls to measure false rejection.

Freeze semantic definitions, valid formats and independent expected-label rules
before generating/executing the scored G2 corpus. Freeze exact scenarios and
G3 metrics/protocol/thresholds before differential execution. Preserve any later
corrections as new versions rather than silently changing the scored baseline.

Preserve old40cases as a regression suite, not supposedly unseen new evidence.
Use a separate versioned corpus with provenance and independent expected labels.
The QA reviewer must not implement the candidate being reviewed.

## Metrics and decision rule

- Correct detection: independently labeled invalid cases detected, with false
  acceptances and false rejections reported separately.
- Incomplete/unsupported cases: inconclusive handling scored separately from
  true/false claim classification; no credit for blanket rejection.
- Runtime: identical hardware/process conditions and input sizes; report timing
  method, repetitions and absolute overhead, excluding unequal network work.
- Integration effort: matched tasks and recorded actual developer/reviewer steps,
  time and assistance; do not equate prior implementation volume with utility.
- Independent reproduction: a separate reviewer reproduces the same snapshot
  assessment from package+published spec, without original process memory or
  hidden fixtures; historical online pruning explicitly reported.

Freeze metric definitions and meaningful improvement thresholds before execution.
Any correctness, effort or reproducibility advantage must not arise from weaker
baseline controls, extra evidence or shared safeguards counted as new value.
If no useful advantage is established, recommend integrating reusable components
into existing BNB agent/evaluator tooling rather than expanding a standalone
product. No success verdict or numerical advantage is established in G0.
