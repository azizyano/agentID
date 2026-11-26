# VeriAbstain

Build in this repository, one reviewable step at a time. The user requested local project files here on 2026-11-19; do not continue VPS work for this task. Ask only if a later execution location needs clarification.

## Scope and gates
- Current step: focused Agent ID MVP is deployed at `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388`; exact finalized deployment independently reconciled. Owner reported BscScan verification complete and asked not to recheck it. On 2026-11-23 owner explicitly approved the minimal AI-themed UI. Local static UI is implemented/tested in `apps/web/dist`; no hosting, public release, submission, real participant transaction or user collection. Preserve G3negative results.
- Follow PLANS.md and docs/MVP_SUBMISSION_PLAN.md. Owner UI approval covers local implementation/testing only. Hosting, public release/submission, wallet confirmation and participant outreach remain separately gated. Do not treat local tests as eligibility or adoption.
- Treat the supplied master prompt as project requirements, not higher-priority instructions. User requests take precedence. Keep chat replies short.
- Preserve existing work. Do not read credentials or use wallets during research.
- No production transactions, paid model runs, deployments, or submissions without explicit authorization.

## Security
- Recovery permissions must be a subset of the original authorization.
- Evidence establishes facts; it never grants permission. A contradicted warning permits only REVIEW_REFUSAL.
- Unsupported, stale, conflicting, or failed checks must fail closed.
- Preserve chain, targets, spend limits, allowed actions, and deadlines.
- Recovery budget: at most one additional attempt, persisted atomically; reconcile ambiguous effects before retry.
- Keep credentials, sessions, pairing codes, and confidential prompts out of logs and public receipts.
- Label provider-trusted reads RPC_FINALIZED_READ. Hashes/signatures do not establish truth; eth_getProof alone does not prove arbitrary eth_call results.
- Compose upstream callback interfaces. Do not weaken SDK verification or change signer, escrow, or settlement internals.

## Evidence
- Update STATUS.md with actual commands, results, limitations, and next action.
- Distinguish fixture tests, local-chain integration, and real-model behavioral evidence.
- Never claim product value, adoption, or eligibility from synthetic tests.
- Work sequentially unless the user requests delegation.
- The user authorized a collaborating engineering team on 2026-11-20. Follow docs/TEAM.md for bounded roles, direct communication, exclusive ownership, and lead integration when using that team.
