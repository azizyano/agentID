# MVP mainnet deployment — owner confirmation step

## Confirmed result

The owner completed the deployment on 2026-11-23. Finalized read-only
reconciliation confirmed transaction
`0xdc67e447b95bb7b50aca824074360051795d2524462ed137cd1df77161956c17`
and contract `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388` as the exact reviewed build.
Do not run the helper again. BscScan source verification remains a separate
public action; UI work remains unapproved.

The read-only preflight for public wallet
`0xb16b77C16773DEF8fA279A1228Eba9308eCD7841` passed on 2026-11-23.
It observed the official Agent ID registry at a finalized BSC block, matched its
name and symbol, simulated the exact creation data to the expected linked
runtime, and found enough BNB for the estimate. Assurance is
`RPC_FINALIZED_READ`, not an independently authenticated state proof.

The wallet does **not** currently hold an Agent ID. That does not block contract
deployment. It must obtain an Agent ID before it can count as one of the genuine
Agent ID holder interactions later.

## Historical one-time helper procedure

1. Open [BscScan](https://bscscan.com/) in the browser containing MetaMask.
2. In MetaMask, select **BNB Smart Chain mainnet** and the public wallet ending
   `7841`.
3. Open browser Developer Tools, select **Console**, and paste the complete
   contents of `artifacts/mvp/deploy-metamask.js`.
4. The script performs fresh finalized-block, registry, exact-runtime, balance,
   gas and account checks before opening MetaMask.
5. In MetaMask verify:
   - network is BNB Smart Chain mainnet;
   - account ends `7841`;
   - action is contract deployment/creation, with no recipient;
   - native value is zero; only gas is charged;
   - displayed gas is acceptable.
6. Confirm only if every item matches.
7. Return only the console line `PUBLIC_MVP_DEPLOY_TXHASH 0x...`.

The script caps maximum native gas cost at `0.001 BNB`. The dated preflight
estimate was `21,161,900,000,000 wei` (about `0.0000211619 BNB`), but MetaMask's
fresh quote is authoritative for the confirmation decision.

If MetaMask is rejected, the helper clears its checkpoint and may be reviewed
again. For any other error or uncertain outcome, **do not retry**. Return the
sanitized error/checkpoint so the public chain can be reconciled first.

No seed phrase, private key, API key, pairing code or session data should ever
be shared.
