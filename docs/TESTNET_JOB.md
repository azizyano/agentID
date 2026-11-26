# Funded-job preparation — BSC testnet only

Current operation: job1765 was created, but its signed quote expired before funding. Read-only reconciliation found OPEN/budget0/allowance0 and client10U intact. [Cancellation and the corrected one-session flow](FUNDING_SESSION.md) supersede the original chat-by-chat funding handoff. No token funding has occurred.

The staged unsigned planner and its tests are implemented. **No funded job exists yet.** Source compatibility is now reviewed; test U funding and signed job inputs remain pending. Nothing in these tools signs, broadcasts, deploys, or loads keys.

## Live inspection

Source comparison at finalized block 143824641, hash `0x5ad41956cdd3a2657056913a75e243bc2a8c24a8d05715a2b8c2b82c7a565a75`, established:

- Commerce proxy: `0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE`.
- The SDK manifest's older implementation remains `0x153783DdBDF5233c591965F04644b1df2d1A7815`; upstream SDK files were not changed.
- Observed implementation: `0x55c3826B39a0F671B2C3E5D0F1372CaD0B911421`.
- Observed implementation code digest: `0xb42935ea4e89b470ea5049cf66d7f1003a5c8d452aef72d78c666577e828380b`.
- Router implementation matches the SDK snapshot; routing/token links and policy whitelist match, contracts report unpaused, dispute window is 900 seconds.
- Local compilation of bnb-chain/apex-contracts revision `f6a3c4ff337158a8a66281c565f3f1562e1287b7` matches the executable runtime after UUPS __self linking and excluding Solidity CBOR metadata. Full runtime including metadata differs. All 37 SDK function shapes and 19 event layouts match.
- The application pin now expects the reviewed implementation AND exact complete deployed runtime digest. Any further address or code drift blocks unsigned drafts.
- Client `0xb16b77C16773DEF8fA279A1228Eba9308eCD7841` has test gas; test U balance remains 0. Provider `0x7d5E9Fc2D79ed404fbfDe64f93b199cFCC1bB3c1` also has test gas.

Evidence: [source comparison](../artifacts/testnet/source-verification.json), [reviewed inspection](../artifacts/testnet/inspection-reviewed.json). This is RPC_FINALIZED_READ, not an independently authenticated execution/state proof or a general contract security audit. It is a dated observation; recheck before signing. Explorer source retrieval was unavailable; source was instead compiled locally and compared as described above.

## Inputs still needed

The public draft [config/testnet-job.draft.json](../config/testnet-job.draft.json) contains both supplied wallets and deployment addresses. Owner approved exactly1testU and expiry one hour from quote creation. These fields are bound into the generated quote request. Next: [sign the provider quote](SIGN_PROVIDER_QUOTE.md); the accepted public signature remains pending.

## Claim test U now

The pinned SDK README links to the [U faucet](https://united-coin-u.github.io/u-faucet/). Its [frontend source](https://github.com/united-coin-u/u-faucet/tree/618c47d388c1d21f23ce65e0a186a1f1f9d05e57) configures chain97 and faucet `0x86e9197CC0F76E4e4aaa7082180945196bBAb5D3`. Read-only inspection confirms that its tokenInstance is the exact job payment token. It currently offers 10 test U, has sufficient balance, and reports this client eligible. A requestTokens simulation succeeds. [Recorded evidence and unsigned call](../artifacts/testnet/faucet-verification.json).

1. Open the faucet link and connect the **client** wallet `0xb16b77C16773DEF8fA279A1228Eba9308eCD7841`.
2. Select BSC testnet (chain97).
3. Click Claim. Review the transaction: target faucet above, method requestTokens(), native value0 plus network gas, calldata `0x359cf2b7`.
4. Confirm in your wallet and retain the transaction hash. The project has not signed or submitted this call for you.

The observed claim amount is 10 U (10^19 atomic units at18 decimals), with a 30-minute wait interval. Availability and amount can change; inspect the wallet/site before confirming. This is test funding, not adoption or real economic activity.

The source mismatch was resolved through compilation and review, not by accepting an arbitrary RPC-reported address. Later changes still require a fresh review and pin update.

## Run locally

Export the public-input schema without RPC:

```powershell
.\.venv\Scripts\python.exe tools\prepare_testnet_job.py --schema --output artifacts/testnet/spec-schema.json
```

Check the incomplete draft:

```powershell
.\.venv\Scripts\python.exe tools\prepare_testnet_job.py --spec config/testnet-job.draft.json --rpc-url https://bsc-testnet-dataseed.bnbchain.org
```

Expected currently: NEEDS_INPUT for budget/deadline/quote, exit2, no network request or transaction draft. Supply only public task/quote data. A job description goes on-chain; confidential prompts and credentials do not belong in it.

Public deployment inspection:

```powershell
.\.venv\Scripts\python.exe tools\inspect_testnet.py --client 0xb16b77C16773DEF8fA279A1228Eba9308eCD7841 --output artifacts/testnet/inspection-latest.json
```

The inspection exits nonzero on a deployment mismatch; the reviewed deployment now passes. Its HTTP calls are read-only. Endpoint reference: [official BSC JSON-RPC documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/).

## Reproduce source comparison

Use an unchanged checkout of bnb-chain/apex-contracts at the revision above in `.research/apex-contracts`. Copy `verification/package.json` and `verification/package-lock.json` to `.research/source-build`, then run:

```powershell
npm.cmd ci --ignore-scripts --no-audit --no-fund --prefix .research/source-build
node tools/compile_commerce.cjs
.\.venv\Scripts\python.exe tools\verify_testnet_sources.py
```

The compiler uses Solidity0.8.28, OpenZeppelin5.4.0, Cancun, optimizer200 runs, viaIR. It does not load the upstream Hardhat configuration or any .env/wallet. Reports include compiler/source/lock digests. Metadata is excluded only for the executable-runtime comparison; only the known UUPS __self immutable is linked, and unknown immutable/link references are rejected.

## Staged flow after blockers are resolved

Each invocation validates fresh provider-selected finalized state and returns at most one unsigned transaction. The client reviews/signs it externally, waits for finality, and runs the planner again with `--creation-tx-hash` after creation. The receipt/event and exact original creation calldata determine the job ID; there is no guessed next counter.

1. CREATE_JOB: authenticated signed quote, explicit provider, router evaluator/hook and bounded deadline.
2. REGISTER_JOB: bind the pinned whitelisted policy to the confirmed job.
3. SET_BUDGET: exact authorized atomic-unit budget.
4. RESET_APPROVAL, if needed: clear a nonzero allowance that differs from that exact budget.
5. APPROVE_EXACT, if needed: approve the commerce proxy for exactly the budget.
6. FUND_JOB: simulate funding the exact job-bound token/budget, then provide an unsigned draft.
7. FUNDED_CONFIRMED: report the verified funded state with no additional transaction.

The provider's signed quote must remain valid throughout this planning flow. An expired quote or changed job requires reconciliation; never rewrite an existing job's signed terms. Gas/fees/nonce are not reserved by the planner; the wallet must estimate and display them. A positive native balance alone does not establish enough gas. Recheck `valid_until` and all transaction fields before signing.

Exit codes: 0 unsigned plan or confirmed funded state; 2 missing public inputs or blocked preflight; 1 invalid input, RPC failure, simulation failure, or output failure. UNSIGNED_PLAN is a draft requiring manual review, not permission to execute or a claim of general safety.
