# Minimal interface design — version 1 draft

Design only. Pydantic models and exported JSON Schemas follow after G1a requirements settle; these types do not exist in executable code yet.

| Contract | Required information |
| --- | --- |
| TaskIntent | operation ID, chain, allowed actions/targets/recipients, spend limits, expiry, accepted effects, objective output criteria |
| AgentObservation | source ID/type, observed time, tool-output digest, explicit observable decision, private evidence reference |
| TypedClaim | allowlisted predicate ID, chain, target, typed arguments, asserted value/operator, requested block context |
| Evidence | observed value, chain, block number and hash, timestamp, source identity, assurance, verifier version, freshness |
| Verdict | SUPPORTED, CONTRADICTED, INCONCLUSIVE, STALE, or ERROR; evidence references and reason |
| RecoveryRecord | operation ID, original authorization digest, atomic attempt count, state, reconciliation references, final outcome |
| EvidenceReceipt | schema version, domain-separated canonical digest, provenance, assurance, verifier identity, public projection and private references |

Factual verification and authorization are separate return values. Recommendation is REVIEW_REFUSAL or ESCALATE; there is no SAFE_TO_EXECUTE verdict. Unsupported claim extraction must return an explicit failure, not invent a predicate.

Proposed read-only calls: `verify(claim, context) -> verdict`, `check_policy(original_intent, proposed_effects, now) -> decision`, `assess_refusal(observation, verdict) -> recommendation`. A later recovery coordinator owns journal transactions; the model does not call a signer directly.
