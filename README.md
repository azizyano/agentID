# VeriAbstain

**An on-chain receipt for an AI agent’s evidence review, gated by Binance Agent ID.**

When one agent hands work to another, a reviewer needs a way to link an assessment to the account that recorded it without publishing the full evidence. VeriAbstain records two fingerprints on BNB Smart Chain: one for the evidence and one for the assessment. The account that records them must hold an Agent ID at the time of the transaction.

[Mainnet contract and source](https://bscscan.com/address/0x8ACF294c769e25dAb44aCbEb83fc401cA0702388#code) · [Deployment transaction](https://bscscan.com/tx/0xdc67e447b95bb7b50aca824074360051795d2524462ed137cd1df77161956c17) · [Hackathon rules](https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf)

## Try it without a wallet

From the repository root, serve the static console and open [the local preview](http://127.0.0.1:4173).

```powershell
py -3.12 -m http.server 4173 --bind 127.0.0.1 --directory apps/web/dist
```

You can explore the console while disconnected. For a runnable example of the underlying evidence workflow, set up the [Python environment](docs/RUNNING.md#recreate-the-environment) and run:

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py doctor
.\.venv\Scripts\python.exe tools\veriabstain.py demo
```

The CLI demo uses simulated evidence to show how the validator checks a structured allowance or escrow-job status against a pinned observation. It runs offline and needs no API key, wallet, or gas. [CLI guide](docs/LOCAL_HANDOFF.md)

## How the on-chain receipt works

1. **Check.** The web MVP runs a built-in contract integrity check. It compares the deployed bytecode with the reviewed build, checks the registry binding, and reads the connected address’s Agent ID status at a finalized BNB Chain block.
2. **Review.** The browser hashes the evidence and assessment locally. It shows both digests and simulates the exact transaction before asking the wallet to approve it.
3. **Record.** The contract checks Agent ID ownership again on-chain and rejects duplicate evidence from the same address. It records the two digests in an event from the holder’s address. A returning address can record fresh evidence while the unique-holder count stays the same.
4. **Reconcile.** The console matches the transaction against the reviewed request before treating it as finalized. The participant can review the transaction on BscScan.

Agent ID controls who can write a receipt through `recordAssessment(bytes32,bytes32)`. The official registry’s `balanceOf(msg.sender)` must be positive. An address without an Agent ID cannot record a receipt. [Contract source](contracts/VeriAbstainEvidenceRegistry.sol)

## What a receipt establishes

A receipt ties the two digests to the sender and block. Someone who has the original inputs can recompute the digests and compare them. The browser’s chain observations rely on its RPC provider. Whether the underlying assessment is true, or any follow-up action is authorized, must be determined separately.

The contract has no owner, upgrade path, or access to user assets. The recording request sends **0 BNB** and the wallet charges network gas. Users review and confirm it in their own wallet.

## Deployment and participation

| Item | Status |
| --- | --- |
| BNB Smart Chain mainnet | Deployment confirmed at `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388` |
| Hosted console | `agentid-web.vercel.app` is deployed. Wallet testing is on hold pending [MetaMask report #316275](https://github.com/MetaMask/eth-phishing-detect/issues/316275). Use the wallet-free preview above. |
| Wallet compatibility | The app uses an injected EVM provider. A successful test with the actual Agent ID holder address in Binance Wallet remains pending. |
| Innovation Award | The rules require a live product and at least 30 distinct Agent ID addresses interacting with the project contract during the submission window. The deadline is December 9, 2026 at 08:00 UTC. |

The first live holder receipt and campaign participation remain to be verified. [Finalized deployment evidence](artifacts/mvp/deployment-confirmed.json) · [Project status](STATUS.md)

## Reproduce the checks

Use the [locked Python environment](docs/RUNNING.md#recreate-the-environment) and the existing Node lockfiles under `verification/` and `verification/wallet-tests/`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/js/mvp_contract_test.cjs tests/js/mvp_deploy_browser_test.cjs tests/js/mvp_deployment_test.cjs tests/js/mvp_ui_test.cjs tests/js/provider_submit_startup_test.cjs
```

The suites cover the evidence validator, receipt preparation, browser wallet behavior with simulated providers, and contract behavior against a local chain. The Python integration suite also runs the argument-driven wallet funding harness. [Deployment guide](apps/web/README.md) · [Receipt preparation](docs/MVP_INTERACTION.md)

## Research background

An earlier EvidenceLab comparison tied its deterministic baseline on all 62 frozen cases and ran slower. That result remains separate from the current Agent ID receipt MVP. The project keeps the original evaluation available so reviewers can see how the scope changed. [EvidenceLab G3 report](docs/EVIDENCELAB_G3.md) · [Original comparison](docs/G1_EXPLORATORY_RESULT.md) · [Threat model](docs/THREAT_MODEL.md)
