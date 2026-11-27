# Existing receipt MVP interaction reference

This guide documents the earlier receipt flow. The active compatibility tester
uses its saved observation as a case and does not require another transaction.
See the [product specification](PROJECT_SPEC.md).

This local, non-UI step binds one validated receipt plan to the deployed MVP
contract and checks the proposed participant against finalized BSC mainnet
state. It sends no transaction and never requests a private key.

```powershell
.\.venv\Scripts\python.exe tools\prepare_mvp_interaction.py `
  --participant 0xPUBLIC_AGENT_ID_HOLDER_ADDRESS `
  --receipt-plan artifacts\mvp\receipt-example\receipt-plan.json `
  --output artifacts\mvp\participants\ADDRESS-interaction.json
```

The preparer fails closed unless all of the following are true:

- chain ID is 56;
- the deployed runtime at `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388`
  matches the reviewed build;
- the contract is configured with the official Agent ID registry;
- the participant currently has a positive Agent ID balance;
- that participant has not recorded the same evidence digest;
- the zero-value call succeeds and its gas estimate is within the reviewed
  bound;
- the finalized observation remains canonical.

The output contains an unsigned transaction intention only. Eligibility and
simulation are provider-trusted observations and can change. A participant must
still inspect BSC mainnet, their selected account, the zero native value,
contract destination, calldata, and fresh gas estimate before explicitly
confirming in their own wallet.

This mechanism must not be used to manufacture eligibility. Each of the target
30 interactions must come from a genuine, independently controlled Agent ID
holder. Repeated receipts from one holder increase `receiptCount` but not
`uniqueAgentCount`. The on-chain receipt is attribution, not proof that its
evidence is true or authorized.

The example receipt uses simulated testnet evidence and is only a development
fixture. Do not present it as live evidence or product value. A public campaign
needs a clearly documented evidence package and usability layer. UI work still
requires the owner's explicit approval before implementation.
