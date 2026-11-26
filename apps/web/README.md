# VeriAbstain MVP web interface

This is a dependency-free static interface for the deployed BSC mainnet MVP.
It is local-only until hosting receives separate owner approval.

## Preview locally

```powershell
.\.venv\Scripts\python.exe -m http.server 4173 --bind 127.0.0.1 --directory apps\web\dist
```

Then open `http://127.0.0.1:4173` in a browser containing MetaMask.

The page makes only read-only wallet-provider calls on startup. Connecting,
switching networks, and recording a receipt each require an explicit user
action. The write request is fixed to BSC mainnet, the deployed contract, exact
locally generated calldata, and zero native value. MetaMask remains the final
confirmation boundary.

## Rebuild pinned configuration

```powershell
node tools\build_mvp_ui.cjs --output apps\web\dist\config.js
```

The generator recompiles the reviewed Solidity source and links the official
Agent ID registry immutable before emitting the exact expected runtime. It
refuses bytecode or compiler-setting drift.

## Deploy on Vercel

1. Push `apps/web` to your Git repository, including `dist/config.js` and the other
   files in `dist`.
2. Import your repository in Vercel and set **Root Directory** to `apps/web`.
   The included configuration selects **Other**, an empty build command, and
   `dist` as the output directory. Leave environment variables empty.
3. Deploy and open the production URL in a browser with the wallet that holds
   the Agent ID. Check that the runtime and holder checks pass and that the
   reviewed digests match the receipt request. Review the contract destination,
   0 BNB value, and network gas in the wallet.
4. Have one willing Agent ID holder complete the flow and check for a finalized
   receipt before sharing the campaign link. If the app shows **Check previous
   transaction**, use it to reconcile the existing request.

## Current scope

- Connect an injected EIP-1193 wallet.
- Require BNB Smart Chain mainnet.
- Show live receipt and unique-holder counts.
- At a finalized block, compare the exact deployed runtime, official registry
  binding, and current Agent ID balance.
- Canonically hash the locally constructed integrity observation and assessment.
- Simulate and request one zero-value `recordAssessment(bytes32,bytes32)` call.
- Reconcile the exact transaction against finalized state and refresh progress.

The receipt is attribution, not proof that an underlying claim is true or that
any action is authorized. No backend, API key, custody, account system, private
upload, analytics, or hosting is included.
