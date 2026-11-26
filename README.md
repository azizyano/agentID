# VeriAbstain

Local read-only validation of structured allowance and job-status analyses,
using independently collected, pinned BSC testnet evidence. An owner-approved
narrower utility following an exploratory refusal-recovery experiment.

## Working commands

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py doctor
.\.venv\Scripts\python.exe tools\veriabstain.py demo
.\.venv\Scripts\python.exe tools\veriabstain.py receipts
```

For a supplied analysis with independent current authorization:

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py check --authorization path/to/current-authorization.json --analysis path/to/analysis.json
```

The demo is offline with simulated chain/worker data. The check command uses
public read-only RPC for reviewed chain97 deployments, validates scope, pinned
block and value, and saves a private receipt. No model key, wallet or transaction
is needed. Acceptance never grants execution permission.

## Current delivery

The hackathon submission pivot now has a first local MVP contract:
`contracts/VeriAbstainEvidenceRegistry.sol`. It permits only current Agent ID
holders to record content-addressed evidence/assessment receipts, counts unique
holder addresses, and has no owner, asset, approval, custody, transfer or
withdrawal operation. Seven contract behavior checks plus the existing four
wallet-startup regressions pass. Deterministic unsigned receipt preparation now
binds the validated envelope, recomputed assessment and explicit assessment
time to exact contract calldata; the current full Python suite is **574 passed**.
The exact approved contract is now deployed on BSC mainnet at
`0x8ACF294c769e25dAb44aCbEb83fc401cA0702388`; finalized receipt, runtime and
initial state reconciliation passed. The owner reports BscScan source
verification completed; the project did not independently recheck it at the
owner's request. The approved AI-themed static UI is now implemented locally;
hosting, submission and user collection have not started. See the
[MVP submission plan](docs/MVP_SUBMISSION_PLAN.md).

An offline deployment package now contains the exact tested creation data,
compiler Standard JSON, ABI-encoded official Agent ID registry constructor, and
BscScan verification manifest. Exact creation data was rehearsed on a local
chain56 and the immutable-linked runtime hash matched. The package has no
deployer, signature, API key or transaction. A subsequent read-only BSC mainnet
preflight passed for wallet ending7841 and a guarded MetaMask helper is ready;
the owner deployed it and the finalized exact deployment was confirmed. Source
verification was owner-reported complete. A participant preparer now
checks finalized Agent ID eligibility, exact runtime/configuration, duplicates,
zero-value simulation and bounded gas before emitting an unsigned intent.

The local interface in `apps/web/dist` adds a responsive proof console: passive
startup reads, explicit wallet connect/network switch, exact runtime and Agent
ID checks at a finalized block, local SHA-256 evidence/assessment commitments,
zero-value simulation, explicit MetaMask confirmation, receipt polling and live
progress toward30 unique holders. It has no backend, analytics, private upload,
API key or custody. Local browser QA passed; hosting remains unapproved.

Reuse the frozen evidence cases directly in an existing pytest suite with [the checker contract helper](docs/REUSE_IN_PYTEST.md). Reference integrations are tested locally; no external agent repository is modified.

EvidenceLab G1 adds a separate versioned evidence envelope and explicit legacy compatibility. [G1 report](docs/EVIDENCELAB_G1.md). G2 adds a separately frozen62case mutation corpus; [G2report](docs/EVIDENCELAB_G2.md). G3found baseline and candidate62/62equal with slower candidate assessment; [G3report](docs/EVIDENCELAB_G3.md). No standalone advantage established; recommend bounded reuse/integration. G4notstarted. Existing CLI behavior is unchanged.

SDK verification/callback composition, independent evidence collection, strict
output validation, durable single-analysis journal, private receipt creation
and offline receipt inspection are implemented. The earlier reuse handoff had
539passing tests; the current full local suite has **589passed**, with one
existing dependency warning.
Real CLI smoke accepted a matching allowance and rejected an incorrect value.

Earlier testnet job1766 completed its user-signed lifecycle with1testU payout.
The exploratory16scenario DeepSeek comparison found C/C_RETRY/D each accepted
one analysis, with no D-only completion. Original G1value gate is **not passed**.
This utility does not imply production readiness, validated economic benefit,
UI/API, automated submissions, mainnet deployment or a receipt registry.

## Guides and evidence

- [Local handoff and command reference](docs/LOCAL_HANDOFF.md)
- [Check an analysis](docs/CHECK_ANALYSIS.md)
- [Private receipt inspection](docs/RECEIPTS.md)
- [SDK application callback](docs/APPLICATION_CALLBACK.md)
- [Independent evidence reader](docs/CHAIN_EVIDENCE.md)
- [Strict deliverable validation](docs/DELIVERABLE_VALIDATION.md)
- [Actual exploratory comparison result](docs/G1_EXPLORATORY_RESULT.md)
- [Current evidence-backed status](STATUS.md)
- [Agent ID MVP submission plan](docs/MVP_SUBMISSION_PLAN.md)
- [Ordered plan and gates](PLANS.md)
- [Source pins](docs/DEPENDENCIES.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Upstream findings](docs/UPSTREAM_AUDIT.md)
- [Environment setup](docs/RUNNING.md)
- [Worker protocol](docs/WORKER_PROTOCOL.md)
- [Testnet integration history](docs/TESTNET_JOB.md)
- [Engineering ownership](docs/TEAM.md)

All files/execution for this task stay local. Fixtures and model observations
remain separate from live chain evidence. RPC reads require provider trust;
receipt hashes prove neither truth nor authorship. Preserve private journals,
never paste API keys, and do not reset ledgers to bypass attempt/spending limits.
