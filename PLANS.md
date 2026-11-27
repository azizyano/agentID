# Active build plan — Agentic Wallet compatibility tester

The owner selected this direction on 2026-11-27. Use the
[product specification](docs/PROJECT_SPEC.md) for scope and record completed
checks in [STATUS.md](STATUS.md).

1. **Completed — local checker.** Versioned the expected action and
   redacted observation inputs for a chain-56 zero-value contract call.
   The CLI reports each check, the evidence level and the reported stage.
2. **Completed — first workflow fixtures.** Modeled the regular-wallet sender mismatch
   and the successful AI Pro preview with missing fee and no App confirmation
   as distinct observations. Added a labeled positive fixture and controls
   for mismatched action fields, stale data and incomplete evidence.
3. **Completed — redacted report export.** Render Markdown from strict cases
   and partial observations with known review blockers. Reproduce the
   owner's historical AI Pro report from saved evidence.
4. **Completed — before-and-after replay.** Compare two saved attempts under
   the same expected workflow. Reproduce the owner's progress from blocked
   precheck to successful simulation with remaining review blockers.
5. **Completed — local compatibility UI.** Open the saved replay, import
   case files and download a report using the same checker as the CLI.
6. **Prepared — hackathon demo and submission.** The static demo is in the
   Vercel output directory. The [submission packet](docs/HACKATHON_SUBMISSION.md)
   documents the project entry, community post and remaining owner actions.
7. **Next — validate with a builder.** Use the [pilot guide](docs/COMPATIBILITY_PILOT.md)
   to compare the result with one willing external
   builder's existing workflow. Record whether the checker catches a mismatch
   or saves time. Obtain approval for outreach and any new live-test work.
8. **Review before expanding.** Add more actions, chat integration or
   Agent ID report attribution after there is evidence that users need them.
   UI, hosting, on-chain actions and release each remain separately gated.

The historical plans below explain the existing code and deployment. The
active milestones are listed above.

## Historical ordered delivery

1. **G0 — foundation and review:** source review and repository foundation recorded. Outstanding deployed-contract checks remain in STATUS.md.
2. **G1a — reproducible fixtures:** implement the 40-scenario manifest and harness against the actual SDK callback path. Run deterministic tests; label simulated contract reads clearly.
3. **G1b — proof of value:** establish a real funded-job integration on an isolated chain, then compare A/B/C/D with a real worker. No paid calls without authorization. Missing infrastructure or credentials means BLOCKED behavioral proof.
4. **G1 decision:** require a reproducible nontrivial C failure fixed by D, with no observed unauthorized or duplicate effects. Otherwise NO-GO or a narrower evidence-backed pivot. Owner reviews before G2.
5. **G2 — core:** typed models, pinned evidence reads, immutable authorization checks, durable recovery journal, objective output validation, private/public receipts. Repeat evaluation; owner reviews.
6. **G3 — workflow:** minimal registry and web flow only after G2 passes. Deployment requires separate approval of chain, deployer, cost, and verification.
7. **G4 — release:** independent review, reproducible demo, source verification, real-user eligibility checks, explicit release/submission approval.

Initial delivery snapshot: G1 fixtures and offline comparison infrastructure hardened by the user-requested team. Real BSC testnet job1766 lifecycle completed. Optional local runtime transport implemented with mocked tests. The original G1 value gate remained unpassed.

2026-11-20 exploratory decision: completed16scenario C/C_RETRY/D subset found1/1/1accepted analyses and no D-only completion. NO-GO for G2 on current evidence; full repeated gate remains pending. Owner review of docs/G1_EXPLORATORY_RESULT.md required before revised scope or further paid experiment.

2026-11-20 owner approved narrower strict deliverable-validation scope. Standalone validator/CLI and31fixture checks complete; independent evidence integration next. Original refusal-recovery value gate remains unpassed. Approval does not include UI/API/contracts or broad production recovery.

Narrowed utility completion: independent evidence reader, strict validator and read-only SDK callback journal composed; offline demo succeeds,284fullsuite tests pass. Further product scope awaits owner review; original G1value gate not passed.

Local narrowed-utility handoff complete: unified CLI and docs delivered,313fullsuite tests pass. No further action required for approved utility scope; broader product requires scope/value review.

## Historical EvidenceLab track

- G0: inspect actual code/artifacts, dependency map and strong deterministic baseline. Completed; docs/EVIDENCELAB_G0.md. No feature code changed.
- G1: versioned Evidence Validity Envelope, temporal/snapshot distinctions and compatibility strategy. OWNER APPROVAL PENDING.
- G2: independently specified deterministic mutation corpus with valid controls. Not approved.
- G3: frozen differential evaluation against equal-scope strong baseline. Not approved.
- G4: local package/reproduction workflow with explicit offline/online assurance/capability limits. Not approved.

Stop after each phase for approval. Continue standalone development only if correctness, integration/review effort or independent reproducibility improves; otherwise recommend integrating into existing tooling. No dashboard/hosted platform/token/registry or original-thesis success is implied.

2026-11-21 EvidenceLabG1 complete: separate envelope/compatibility/types with63new focused checks;376fullsuite tests pass, independent QA cleared. See docs/EVIDENCELAB_G1.md. G2requires owner approval of separate mutation corpus/test scope and predeclared semantics/validformats/expectedlabels; G3/G4 remain unapproved. No measured added value yet.

2026-11-21 EvidenceLabG2 complete: predeclared/frozen62case synthetic corpus, all outcomes matched,14validcontrols no false rejection;453fullsuite passes. Independent G2QA reviewed recipes/oracle. See docs/EVIDENCELAB_G2.md. G3fair differential evaluation awaits explicit owner approval; G4notapproved. No differentiated value claimed.

2026-11-21 G3scored run: strongbaseline andcandidate62/62equal; candidate11.52xmedian/18.41xp95 localassessmentoverhead, no correctness/runtime advantage.526fullsuite tests pass; independentartifactaudit/replay confirm. EffortNOT_MEASURED. NO-GO standaloneexpansion on this evidence. Stopfor boundedintegration/newexperiment ownerdecision; G4notstarted. See docs/EVIDENCELAB_G3.md.

Owner accepted G3no-go and approved boundedreuse, with explicit ask-before-UI instruction. Pytest integration helper delivered:539fullsuite tests pass, source-reviewed independentQA. See docs/REUSE_IN_PYTEST.md. No externalagentrepo/UI/productionflow modified. Future broaderwork needs concrete target/scope and UI approval before implementation.

2026-11-21 hackathon pivot: owner directed an eligibility-first Agent ID MVP, followed by30 genuine Agent ID holder interactions, then improvements before the 2026-12-09 08:00UTC deadline. First reviewable step is a local, noncustodial Agent-ID-gated evidence receipt contract and local-chain behavior tests. Mainnet deployment/wallet/public submission require explicit authorization. Ask before any UI work. Preserve the G3 no-go and distinguish the new submission pivot from proof of the original thesis. See docs/MVP_SUBMISSION_PLAN.md.

2026-11-23 MVP step2: deterministic receipt preparation complete. Validated envelope + recomputed no-authorization assessment + explicit time are domain-separated SHA256 canonical payloads; unsigned chain56 calldata has no destination and zero value.11focused Python checks, Python-to-Solidity calldata execution,9Node checks and550full Python tests pass. Example remains SIMULATED_READ/authenticity NOT_ESTABLISHED. Next prepare deployment/BscScan verification inputs locally; do not deploy or start UI without explicit approval.

2026-11-23 MVP step3: offline deployment/BscScan package complete. Recompiles exact tested source/settings, binds official registry constructor, emits Standard JSON/unsigned creationdata/verification manifest and no deployer/signature/key/address. Initial local rehearsal correctly exposed hashing the unlinked immutable template; fixed by substituting all compiler-reported immutable slots before expected runtime hash. Exact creationdata then deployed on local chain56 with matching runtime/registry.6focused/15combined Node tests pass; last full Python remains550. Stop for explicit owner approval before wallet-specific mainnet deployment. UI still requires separate ask/approval.

2026-11-23 MVP step4: owner response to mainnet-preparation approval proceeded to read-only mainnet preflight. Official registry finalizedcode/name/symbol and exact creation simulation matched; deployer7841 balance3294368808872796wei exceeds maximum estimate21161900000000wei, but holds0AgentID. One-time BscScan-origin MetaMask helper exported with exact runtime comparison, fresh gas/balance/account/chain checks,0.001BNB cap and ambiguous-effect checkpoint.7focused preflight,3browser helper,18combined Node and557full Python tests pass.0transactions. Await owner manual confirmation/hash; reconcile before verification. No UI.

2026-11-23 MVP step5: owner-supplied mainnet deployment hash independently reconciled at finalized state. Exact approved creation from wallet7841 deployed `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388`; creation/runtime hashes, official AgentID registry immutables, chain constant and zero initial counts match. Actual gas cost0.00001743815BNB, value0.17focused fail-closed confirmation tests and574full tests pass; verifier sent0transactions. Deployment alone proves neither source verification nor eligibility/adoption. Next prepare and, only with separate owner approval, submit exact BscScan source verification. UI still requires explicit advance approval.

2026-11-23 MVP step6: owner reported BscScan verification complete and asked not to recheck it; therefore source-verification status is OWNER_REPORTED, not independently confirmed. Non-UI participant preparation is complete: serialized receipt plans are rebuilt exactly, and a public-address read-only mainnet preflight requires approved runtime/configuration, current AgentID balance, no duplicate, sane counters, canonical finalized state, successful zero-value simulation and bounded gas before emitting an unsigned intent.26focused/589full tests pass; no real participant address, wallet action, transaction, user or UI. Next ask owner explicitly for minimal UI approval; otherwise first holders must use the manual CLI/BscScan path.

2026-11-23 MVP step7: owner explicitly approved an AI-themed modern UI for genuine-holder conversion. Local dependency-free static interface implemented in `apps/web/dist`: live counters, explicit wallet/network actions, exact runtime/official registry/current AgentID checks at finalized state, canonical local SHA256 evidence+assessment, duplicate check, zero-value eth_call, explicit MetaMask transaction, ambiguous/pending messaging and receipt polling. Startup is read-only.6UI tests and21scoped Node runner tests pass; prior589 Python suite retained. Local HTTP200 and mobile414px visual QA passed with no overflow/console error; QA found/fixed premature hidden record-button visibility. No real MetaMask E2E, hosting, release, wallet transaction, participant or submission. Next requires owner review, then separate hosting approval before publication and user outreach.
