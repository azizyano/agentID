# G1 exploratory result — 2026-11-20

Decision: **NO-GO for G2 on current evidence.** The completed exploratory subset
did not demonstrate a task-completion improvement over trusted direct reads.
This does not establish that improvement is impossible elsewhere.

| Arm | Selected scenarios | Accepted analyses |
| --- | ---: | ---: |
| C: trusted read | 16 | 1 |
| C_RETRY: trusted read plus reconsideration control | 16 | 1 |
| D: typed assessment and bounded reconsideration | 16 | 1 |

All three accepted the same allowance false-warning scenario. There were zero
D-only accepted analyses over C. Two qualified C_RETRY reconsiderations ended
in invalid outputs. D escalated the two selected ABI-mismatch cases while C's
deliverables failed grading. That is a useful diagnostic, but does not satisfy
the specified completion-value gate. D also produced five rejected deliverables.

Deterministic policy and prior-effect guards blocked or retained operations in
the authorization/duplicate controls. No external asset operation was performed
by this evaluator. These observations do not prove general action safety.

The frozen subset covers all ten conditions and both predicates, with sixteen
matched scenario triplets. It is exploratory, selected after inspecting the
five-request pilot, and lacks the full forty-scenario repeated experiment. The
global replay still has147requests pending outside the completed subset. Model
responses came through the owner-executed DeepSeek adapter; underlying predicate
reads were simulated. Replay remains explicitly unattested.

Across pilot and paired calls,55provider responses are recorded. Provider usage:
46,704input and5,555output tokens. Conservative reservations total$1.10 of the
approved$2; reviewed maximum-rate estimate is$0.0206772. Actual billing was not
checked. Do not reset the journal or interpret reservations as charges.

Evidence: `artifacts/private/deepseek/paired-final-summary.json`, frozen
`paired-plan.json`, cumulative replies and durable budget journal; graded
`artifacts/g1b/results.jsonl`. Original failed outputs and prompts retained.

Recommended owner decision: consider a narrower **structured evidence and output
validation** scope, with explicit unsupported/stale/ABI checks and objective
deliverable grading, rather than claiming demonstrated refusal-recovery value.
Its incremental utility must be separately tested against the same common guards
and trusted-read baseline. Existing output validation is already shared by all
arms, so these results do not establish a new differentiated product.

Pause paid experiments and G2 implementation until owner reviews the gate result
and approves either a revised experiment or narrower scope. No new deployment,
wallet action, or API credential is needed for that review.
