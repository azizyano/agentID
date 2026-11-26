# Sign the approved provider quote

Current operation: exact cancellation of unfunded job1765 is finalized and verified. Original signed quote is preserved. Use quote-attempt2 below for the single reserved additional attempt. Return the provider signature promptly; the next client flow combines all funding steps into one session, each with explicit wallet confirmation.

Owner approved the read-only allowance-analysis job, exactly **1 test U**, and expiry one hour from quote creation. This step signs the provider's job terms; it sends no transaction and consumes no gas. Client funding transactions still require separate wallet confirmations. The project never requests private keys or seed phrases.

The pinned SDK uses EIP-191 signing of the **ASCII 0x-prefixed negotiation hash**, not signing the raw32 hash bytes. See [MetaMask personal_sign guidance](https://docs.metamask.io/metamask-connect/evm/guides/sign-data/). The helper uses personal_sign only, matching actual SDK verification. It does not request eth_sign, typed asset authorizations, token approval, or transaction submission.

## MetaMask browser extension

1. Select provider `0x7d5E9Fc2D79ed404fbfDe64f93b199cFCC1bB3c1` and BSC testnet97 in MetaMask. Connect that provider account to the already-used [U faucet](https://united-coin-u.github.io/u-faucet/).
2. In this project folder, run the command below immediately before signing. It preserves an active request; only expired unsigned requests can be renewed. A saved signed job blocks renewal.

```powershell
.\.venv\Scripts\python.exe tools\prepare_job_quote.py --output artifacts/testnet/quote-attempt2
```

3. Review `artifacts/testnet/quote-attempt2/request.json`. It includes the exact task, client/provider, payment token, budget, contract, and timestamps. The quote is valid for15minutes and the job expiry is one hour from its creation.
4. Open `artifacts/testnet/quote-attempt2/metamask-sign.js` and copy its text. On the faucet tab, open the browser Console with Ctrl+Shift+J, paste the helper, and press Enter. Review the helper first: it checks the network/account/expiry and requests only a personal message signature. If the browser blocks pasting, report the message rather than disabling protections.
5. MetaMask opens a **Sign message** confirmation. Check that the account is the provider and the message exactly matches `artifacts/testnet/quote-attempt2/message.txt`. Confirm only that message. The console prints `PUBLIC_PROVIDER_SIGNATURE` followed by a public0x signature.
6. Return that public signature in this chat. Do not send wallet secrets. An expired quote is rejected even if signed successfully; prepare a fresh unsigned request only before any job has been created.

The helper is a developer signing script, not a product UI or a wallet/session service. It has no fetch, relay, pairing, key storage, approval, or broadcast code. The wallet's explicit confirmation remains the signing boundary.

## Import and preflight

The lead saves only the returned public signature in a local file and runs:

```powershell
.\.venv\Scripts\python.exe tools\prepare_job_quote.py --output artifacts/testnet/quote-attempt2 --signature-file artifacts/testnet/provider-signature.txt
.\.venv\Scripts\python.exe tools\prepare_testnet_job.py --spec artifacts/testnet/quote-attempt2/signed-job.json --rpc-url https://bsc-testnet-dataseed.bnbchain.org
```

Import recomputes the request from the approved proposal, checks exact scope and expiry, recovers the provider with the SDK's EIP-191 semantics, and applies upstream description limits. The planner then reads current finalized chain state and simulates one unsigned next step. No transaction is sent by either command. Existing signatures/receipts or ambiguous effects must be reconciled before creating another job.
