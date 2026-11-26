# Source and dependency ledger

Inspected 2026-11-19. Documentation pages are mutable; inspection date is not an immutable document revision.

## SDK pin

- Repository: https://github.com/bnb-chain/bnbagent-sdk
- Revision: `260e16196931780d0370bd3a9d9b67ece744bb9d`
- Commit timestamp: 2026-11-11T15:53:05+08:00
- Declared Python version: 0.5.1 (`python/bnbagent/_version.py`); Python >=3.10.
- Immutable [source tree](https://github.com/bnb-chain/bnbagent-sdk/tree/260e16196931780d0370bd3a9d9b67ece744bb9d).
- Key sources: `python/bnbagent/erc8183/job_ops.py` (submit_result 351, verify_job 643, watcher 1128); `python/examples/agent-server/src/erc8183_server.py` (app/callback 343 onward); `python/bnbagent/erc8183/schema.py`; `python/bnbagent/storage/storage_provider.py`; `python/tests/test_funded_watcher_verification.py`; selected cases in `python/tests/test_erc8183_job_ops.py`; `ARCHITECTURE.md`; Python README provider section.
- G1a: checked out locally under ignored `.research/bnbagent-sdk`; installed from the same immutable Git revision. The harness composes the real watcher/verifier through test-only client injection. SDK's web3 range is >=6.15.0,<8.

## Official requirements and identity

- [Event and Agent ID interface](https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf): BSC `0x60b9262456de011f7d15a54cdd8c48baaa8b022f`, SPACE ID Agent ID, symbol AI, non-transferable ERC-721. `balanceOf(address) > 0` indicates a holder.
- This name.ai identity is separate from the SDK's ERC-8004 identity registry.
- [Explorer target](https://bscscan.com/address/0x60b9262456de011f7d15a54cdd8c48baaa8b022f#code) could not be inspected. Actual code/proxy identity and a pinned-block holder read remain UNPROVEN; do not deploy against an assumed ABI.
- [Wallet overview](https://web3.binance.com/en/dev-docs/products/agentic-wallet/introduction) and [installation](https://web3.binance.com/en/dev-docs/products/agentic-wallet/install) inspected. No SDK compatibility with this wallet has been demonstrated. Do not infer support from other wallet providers.
- [BSC finality API](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/bsc-api-list/) documents `safe` and `finalized` block tags. Provider support must be tested; no silent fallback to latest.
- [Explorer Foundry verification](https://docs.etherscan.io/contract-verification/verify-with-foundry) inspected as the explorer-family reference. BSC-specific verification remains a later deployment prerequisite; no verification was attempted.

## Local foundation

- Local interpreter: Python 3.12.4, Windows; project `.venv` created locally at user request.
- pytest ==9.2.0 and pytest-asyncio ==1.5.0; PyPI metadata inspected. Direct versions in requirements-test.txt; runtime/test resolutions in requirements-test.lock.
- G1b declares Pydantic ==2.14.4 directly for experimental worker output contracts (already installed transitively); offline lock regeneration succeeded without installing new packages. No model client package or runtime was added.
- Resolved SDK dependencies include web3 ==7.16.0, eth-account ==0.13.7, and Pydantic ==2.14.4. No production Pydantic contracts implemented.
- `uv pip check`: 50 installed packages compatible. Archive hashes and immutable SDK Git revision recorded; isolated package-build dependencies are not locked.
- No frontend, API, Solidity tooling, Agentic Wallet CLI, or paid model client installed.

## 2026-11-20 live testnet compatibility check

Read-only finalized block143818825/hash0x9b257501f6e2ac782d2f9b89e2e1b19ae2b04c9754863c29d2348f6f62de6b49 shows commerce implementation0x55c3826B39a0F671B2C3E5D0F1372CaD0B911421, differing from the source manifest0x153783DdBDF5233c591965F04644b1df2d1A7815. No override accepted. Evidence is in artifacts/testnet/inspection-latest.json. New implementation verified source was unavailable; ABI/source equivalence is UNPROVEN. Existing router/policy/token read links match the snapshot. Source README approval-floor descriptions are stale relative to client.py, which uses exact approval by default; planner follows executable ABI/code and caps approval to the explicit budget.

Subsequent resolution: cloned [bnb-chain/apex-contracts](https://github.com/bnb-chain/apex-contracts/tree/f6a3c4ff337158a8a66281c565f3f1562e1287b7) at f6a3c4ff337158a8a66281c565f3f1562e1287b7. The observed implementation is also listed in its QA manifest. Local solc0.8.28/OpenZeppelin5.4.0 build matches executable runtime after UUPS __self linking and metadata exclusion; full metadata-inclusive runtime differs. All37 SDK function shapes and19 event layouts agree. Exact deployed code digest is now application-pinned, with upstream SDK unchanged. Evidence: artifacts/testnet/source-verification.json and inspection-reviewed.json; compiler dependencies locked in verification/package-lock.json.

U faucet: linked by pinned SDK python/README.md; frontend source [united-coin-u/u-faucet](https://github.com/united-coin-u/u-faucet/tree/618c47d388c1d21f23ce65e0a186a1f1f9d05e57), revision618c47d388c1d21f23ce65e0a186a1f1f9d05e57. At finalized block143824296, faucet0x86e9197CC0F76E4e4aaa7082180945196bBAb5D3 points to the exact configured payment token, offers10U, reports client eligible and has sufficient balance. Read-only requestTokens simulation succeeded. No claim submitted by the project. Evidence: artifacts/testnet/faucet-verification.json.
