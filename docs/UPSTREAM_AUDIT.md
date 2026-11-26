# Upstream compatibility findings

Revision and immutable source tree: [260e161](https://github.com/bnb-chain/bnbagent-sdk/tree/260e16196931780d0370bd3a9d9b67ece744bb9d). This is a targeted source review, not a completed security audit or executed experiment.

## Existing behavior

- `verify_job` checks FUNDED status, assigned provider, configured router/hook, registered whitelisted policy, expiry, payment asset, service price, and signed negotiation terms by default. Legacy/unsigned opt-outs exist; do not enable them merely to make our experiment pass.
- Signed-quote verification binds authenticated content and funding timing. The verified snapshot replaces unsigned description fields before application work.
- The dispute-window lookup catches errors and continues without its local submission-deadline check. This is an observed upstream behavior, not evidence of an exploitable bypass; keep independent fail-closed deadline handling in the proposed application layer.
- `submit_result` requires a signer, calls `verify_job` again, bounds payload sizes, builds a versioned manifest, uploads it, and submits its canonical keccak256 digest. It does not validate arbitrary factual correctness of the response text.
- `funded_job_watcher` verifies before every callback/retry; default attempt cap is five. It does not sign, submit, or settle itself. Retry/seen state is in memory, so it is not our durable recovery journal.
- The reference HTTP application's `on_job(job)` returns text or `(text, metadata)`. The app subsequently calls `submit_result`. Its per-process processing/retry sets are not cross-process idempotency guarantees.
- The manifest hash binds bytes and context, not truth. Storage supplies upload/download/exists and hashing, not factual verification.

## Actual integration seam

Compose `ERC8183JobOps` and `funded_job_watcher` using an application callback. Capture the worker's explicit structured decision there; verify supported predicates; keep original authorization outside model-controlled data; validate accepted output before calling the ordinary submission path. Never return a refusal as normal accepted work accidentally.

The HTTP example is application-owned reference code, not an SDK server API. Do not modify upstream to insert a bypass. A keyless fixture phase uses a submission recorder; this is explicitly simulated external I/O, not evidence of a real funded job.

## Test evidence reviewed

Read watcher tests covering signed/unsigned quotes, underfunding, wrong provider/status, expiry, fresh verified snapshots, invalid signatures, capped attempts, transient errors, and retry revalidation. G1a executed the selected watcher-verification, job-ops, and schema files: 149 passed. The complete upstream suite has not been reviewed or run. Raw output: artifacts/g1a/upstream-test-output.txt.

## Open gates

No demonstrated false-refusal failure, no C-versus-D benefit, no real model run, no local funded-job environment, and no Agentic Wallet compatibility result. The strongest baseline already has correct prompting and a trusted direct read; typed verification might add no material value. G1 must settle that question.
