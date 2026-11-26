# Threat model

## Trust boundaries

```text
Human authorization (trusted, immutable intent)
    | policy evaluation outside model control
Verified SDK job snapshot -> application worker
Untrusted tool text ------> observation/claim parser (data only)
Supported typed claim ----> configured read-only provider
Provider + pinned block -> factual evidence (provider-trusted)
Evidence + intent -------> refusal review / escalation
Journal + acceptance ---> ordinary SDK submission boundary
Private evidence -------> allowlisted public receipt projection
```

Model decisions, tool text, job content, remote sources, and RPC replies are untrusted inputs. Signed content authenticates origin, not factual truth. A compromised trusted provider can lie; this MVP does not independently authenticate consensus or arbitrary call execution.

## Twelve adversarial hypotheses

1. False warning causes refusal of a legitimate analysis task: verify exact predicate and retain original decision.
2. Genuine warning is mislabeled false: preserve contrary evidence and forbid automatic action.
3. Old state is treated as current: record block number/hash and enforce an explicit freshness budget.
4. Wrong chain/target/spender is substituted: bind all claim arguments to the original task.
5. Proxy/ABI mismatch changes meaning: unsupported code/interface context becomes INCONCLUSIVE.
6. Provider outage triggers optimistic success: return ERROR, never execute.
7. Malformed, unreadable, or ambiguous evidence is coerced into a typed claim: reject unsupported parsing.
8. Conflicting providers or changed block hashes are ignored: stop with INCONCLUSIVE and preserve provenance.
9. Correct factual evidence bypasses an independent restriction: recheck unchanged actions, recipients, amounts, chain, and deadline.
10. Concurrent workers or replay submit twice: journal atomic claims and stable operation identity.
11. Crash after an ambiguous external effect causes blind retry: reconcile before allowing any further attempt.
12. Receipt/logging leaks confidential prompts or sessions, or reuses a digest across domains: allowlisted public fields and versioned, chain/application-bound commitments.

## Recovery conditions

At most one additional recovery attempt, independent of upstream poll retries. Persist the budget before worker reconsideration. Reuse operation identity across restarts and callbacks. A stale read, failed policy check, unknown submission result, or expired task requires escalation/reconciliation, not automatic retry. Public hashes of predictable private values can leak information; do not publish raw private-data hashes as a privacy guarantee.
