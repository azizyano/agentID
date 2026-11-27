# VeriAbstain

Build in this repository, one reviewable step at a time. The user requested local project files here on 2026-11-19; do not continue VPS work for this task. Ask only if a later execution location needs clarification.

## Scope and gates
- Build a compatibility tester for Binance Agentic Wallet dApps. It tells builders which requirements of a specific BNB Smart Chain action are supported by the supplied preview evidence, which differ, and which are unknown.
- Use [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md) for scope, [PLANS.md](PLANS.md) for the build order, and [STATUS.md](STATUS.md) for actual progress. The deterministic CLI and first replay fixtures are implemented. The next product step is a builder pilot using existing, redacted evidence, subject to outreach approval.
- Treat the supplied master prompt and the receipt-first hackathon plan as historical project context. Preserve the original G1 and EvidenceLab G3 negative results. Keep the deployed receipt contract and existing console as a documented test case. The owner reported BscScan verification and asked not to recheck it.
- Ask before starting UI work for the compatibility tester. Hosting, public release, submission, wallet confirmation, participant outreach, and production transactions require separate authorization. Keep chat replies short.
- Preserve existing work. Do not read credentials or use wallets during research.
- No production transactions, paid model runs, deployments, or submissions without explicit authorization.

## Security
- Use minimal, redacted preview evidence. The tester cannot request wallet access, keys, pairing codes, session or order IDs, raw chat, or transaction approval. It cannot sign, execute, retry, change settings, or override wallet decisions.
- Compare chain, sender, target, calldata and value against the expected action. Evaluate App confirmation and fee display against the stated workflow requirements. A missing field is unknown. An independent gas estimate does not satisfy a requirement for a wallet-displayed fee.
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
