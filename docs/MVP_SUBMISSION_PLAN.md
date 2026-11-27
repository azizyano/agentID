# Historical Agent ID hackathon receipt MVP

The receipt deployment and pilot are the first compatibility case for the
current [project specification](PROJECT_SPEC.md). The sequence below records
the November 21 plan. The [active build order](../PLANS.md) supersedes it.

Owner direction on 2026-11-21: prioritize a submission-eligible MVP, then obtain
30 genuine Agent ID holder interactions, then improve the product before the
deadline. The owner explicitly approved local minimal UI implementation on
2026-11-23; hosting and public release remain separately gated.

## Focused product

**VeriAbstain Evidence Gate** lets an Agent ID holder validate a prepared
evidence package locally and record only the evidence and assessment digests on
BNB Smart Chain. Agent ID is part of the core authorization path: the contract
checks the official Agent ID registry and rejects non-holders.

The receipt is attribution, not truth. It does not authorize recovery, spending,
or execution and it does not place confidential evidence on-chain.

## Eligibility-first sequence

1. Build and behavior-test the minimal Agent-ID-gated receipt contract locally.
2. Review contract safety and deterministically bind a validated envelope,
   recomputed assessment, and explicit assessment time to the two receipt
   digests. Generate unsigned calldata without a contract destination.
3. Obtain explicit owner approval for deployment parameters and wallet actions.
4. Deploy on BSC mainnet and verify/open-source the exact source on BscScan.
5. Build and locally test the owner-approved minimal website/UI.
6. Make the live path usable, publish instructions, and submit early.
7. Invite at least 30 genuine Agent ID holders. Each independently calls the
   submitted project contract; no bots, bulk accounts, wash activity, or paid
   fake interactions.
8. Improve clarity and product depth only after eligibility evidence is sound.

## MVP contract boundaries

- Official mainnet Agent ID registry:
  `0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F`.
- Current holder status checked with `balanceOf(msg.sender) > 0` on every write.
- Nonzero evidence and assessment digests required.
- Same holder cannot record the same evidence digest twice.
- Counts total receipts and distinct participating holder addresses.
- No owner, upgradeability, token, value transfer, approval, custody, pause,
  withdrawal, privileged mutation, or payable function.
- A registry error fails closed.

## Current evidence level

Finalized RPC reconciliation establishes that the exact approved contract is
deployed on BSC mainnet at `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388`.
It does not establish BscScan source verification, a live product, product
value, submission acceptance, or 30-user eligibility. Those require later,
separately recorded evidence; current on-chain receipt and unique-holder counts
were both zero at the deployment confirmation snapshot.

## Deterministic receipt command

The local preparer requires an explicit assessment time and emits one unsigned
plan. It does not accept a contract destination and cannot submit a transaction:

```powershell
.\.venv\Scripts\python.exe tools\prepare_mvp_receipt.py `
  --evidence examples\evidencelab\envelope-v1-allowance.json `
  --now 1000 `
  --output artifacts\mvp\my-receipt
```

The plan commits a normalized, schema-validated envelope and a locally
recomputed assessment. The assessment payload also commits the evidence digest
and explicit assessment time. The included calldata is exactly
`recordAssessment(bytes32,bytes32)` with zero native value. The example is
`SIMULATED_READ`, not live evidence or a claim of authenticity.

## Offline deployment package

The deployment preparer recompiles the exact tested source and refuses any
bytecode drift. It produces Solidity Standard JSON, ABI-encoded constructor
arguments, exact unsigned creation data, expected runtime hash, and a BscScan
verification manifest:

```powershell
node tools\prepare_mvp_deployment.cjs --output artifacts\mvp\deployment-package
```

The package intentionally contains no deployer, nonce, predicted address,
signature, API key, or transaction. Creating it is not deployment or source
verification. Those actions remain separately gated.

BscScan uses the Etherscan verification family. Its verification flow recompiles
the submitted source/settings and compares deployed bytecode; constructor values
must be supplied as ABI-encoded hex. References:
[BscScan verification](https://bscscan.com/verifyContract) and
[constructor arguments](https://etherscan.io/help/etherscan/developer/contract-verification-constructor-arguments).

The current public-wallet preflight and one-time owner confirmation instructions
and confirmed result are in [MVP_MAINNET_DEPLOY.md](MVP_MAINNET_DEPLOY.md).
The exact deployment is finalized. The owner later reported completing BscScan
source verification and asked that it not be independently rechecked.
