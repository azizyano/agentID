# One-session wallet funding flow

## Why job1765 needs reconciliation

The owner created job1765 with transaction `0x20876edfa2217bf193f3135fec8ee603643ce08dedecc8f25b096993e83cf0a9`. The first immediate preflight encountered an unfinalized creation; the subsequent finalized read succeeded. The quote expires15minutes after negotiation, so chat-turn-by-turn wallet instructions were too slow. The original quote expired before registration/funding.

Read-only reconciliation confirms OPEN status, budget0, allowance0, and the client's10U balance. No U entered escrow. Creation used test gas. The original signed terms are retained and must not be extended or replaced inside the existing job.

## Cancel the unused job

The client can reject an OPEN job under the upstream contract. The prepared helper validates the exact reconciled zero-budget context, known implementation/code, selected client and chain, then simulates reject() before opening a MetaMask confirmation. It never signs or confirms for the user.

1. Select client wallet ending7841 on BSC testnet97, connected to the U faucet.
2. Review `artifacts/testnet/cancel-unused-job.js`. Run it in that faucet tab's Console.
3. Review cancellation/reject of job1765: native value0, wallet-displayed gas only. This changes the unused job to REJECTED and moves no U.
4. Return `PUBLIC_CANCEL_JOB_TXHASH`. The project must confirm finalized cancellation before archiving the old signing context or requesting a new quote.

The helper refuses a changed/funded/nonzero-budget job, and uses a Web Lock plus a local checkpoint to prevent concurrent or duplicate requests. Unknown effects must be reconciled, not retried blindly. User cancellation is an explicit wallet action, not already performed.

## Replacement funding session

The replacement session is implemented and tested with actual ethers6.13.4 ABI encoding/decoding and simulated wallet/RPC. It requires a **fresh quote**, preserving the approved task, participants, token, exactly1U budget and one-hour duration. No production contract, UI, API, signing key or automatic wallet confirmation is added.

After cancellation is verified and a new provider quote is explicitly signed, the lead performs current read-only preflight and exports the helper:

```powershell
.\.venv\Scripts\python.exe tools\export_funding_session.py --plan PATH_TO_FRESH_CREATE_PLAN --spec PATH_TO_FRESH_SIGNED_JOB --output artifacts/testnet/funding-session.js
```

The helper runs in the HTTPS U faucet tab with the client wallet. It opens separate MetaMask confirmations for createJob, registerJob, setBudget, exact approve, and fund. A nonzero mismatched allowance adds a separate approval-reset confirmation. Each action is exact and bounded, with native value0; MetaMask displays gas. No confirmation is bypassed or auto-accepted.

Between steps it waits for finalized receipts, recovers the actual JobCreated ID, verifies original calldata and job fields, checks code/implementation/route/token/policy state, and simulates the next transaction. Web Locks serialize same-origin sessions. Local checkpoints retain known hashes and ambiguous requests; resume reconciles saved transactions before proceeding. These are development helper guards, not an authenticated production journal or a guarantee across other origins/devices.

At least five quote minutes must remain before a new create and at least two before funding. A user can still leave a wallet prompt open too long; the helper cannot force confirmation timing. If the window becomes too short, it stops and requires reconciliation. It never extends a quote or funds an expired one automatically. The final receipt's funding timestamp is checked against quote expiry.

When completed, Console prints PUBLIC_FUNDED_JOB with creation/funding hashes and job ID for independent backend verification. Simulation tests do not establish a real funded job or AI value.

## Reproduce helper tests

Copy `verification/wallet-tests/package{,-lock}.json` into `.research/wallet-tests`, then:

```powershell
npm.cmd ci --ignore-scripts --no-audit --no-fund --prefix .research/wallet-tests
.\.venv\Scripts\python.exe -m pytest tests/integration/test_wallet_funding.py tests/integration/test_cancel_job_step.py -q
```

The tests cover full bounded flow, exact/reset approvals, replay, concurrent sessions, wrong chain/account/code/job context, short/expired window, wallet rejection, and ambiguous/post-broadcast errors. They do not connect to a wallet or network.
