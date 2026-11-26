# VeriAbstain MVP web interface

This is a dependency-free static interface for the deployed BSC mainnet MVP.
It is local-only until hosting receives separate owner approval.

## Preview locally

```powershell
.\.venv\Scripts\python.exe -m http.server 4173 --bind 127.0.0.1 --directory apps\web\dist
```

Open `http://127.0.0.1:4173`. Use any browser for the Agentic Wallet prompt or
a compatible extension for the connected-wallet flow.

The page makes only read-only wallet-provider calls on startup. Connecting,
switching networks, and recording a receipt each require an explicit user
action. The write request is fixed to BSC mainnet, the deployed contract, exact
locally generated calldata, and zero native value. MetaMask remains the final
confirmation boundary.

The console shows the full connected address and offers a selector when the
wallet exposes multiple accounts. **Disconnect** clears the local selection and
any prepared receipt in the current tab. It preserves unresolved transactions.
To end the wallet's site permission, use the wallet's connected-sites settings.
If Binance exposes only your regular wallet, the console cannot select an
Agentic Wallet address that Binance has not exposed.

## Binance Agentic Wallet

1. Open [Binance AI Pro](https://ai.binance.com/) and sign in to your Agentic
   Wallet there. Binance documents built-in wallet tools for AI Pro accounts.
   This custom call also needs active Developer Mode in the Binance App.
   [AI Pro setup](https://web3.binance.com/en/dev-docs/products/agentic-wallet/ai-pro) · [Developer Mode](https://web3.binance.com/en/dev-docs/products/agentic-wallet/use-cases/developer-mode)
2. In VeriAbstain, select **Use your Agent ID**, enter the public Agentic Wallet
   address, then select **Prepare agent prompt**. The browser checks the
   deployed contract, registry and holder eligibility through BNB Chain RPC,
   and simulates the exact zero-value call. No browser wallet connection is
   needed.
3. Select **Copy prompt** and paste it into your signed-in AI Pro chat. You can
   also use an agent already connected through Binance's official skill or
   copy the preview command for the official CLI. Keep VeriAbstain open.
4. Check the preview for the exact sender, contract, calldata, chain and zero
   BNB, acceptable gas, and no warnings or unexpected balance, allowance or
   authority changes. Stop if anything differs, expires, or if
   `requireConfirmation` is anything other than `true`. The prompt requests a
   preview first and requires separate approval before Binance App confirmation.
   [Binance external signing reference](https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/binance-agentic-wallet/references/external-sign.md)
5. After approving in the Binance App, paste the public transaction hash into
   **Verify finalized receipt**. The page checks it against the original
   prepared call. While a result is unknown, check the same hash or reconcile
   wallet activity before preparing another receipt.

Only a successful on-chain call from an Agent ID holder can change the
contract's unique-holder count. AI Pro execution of this specific call still
needs a first live pilot.

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
