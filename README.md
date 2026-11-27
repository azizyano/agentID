# VeriAbstain

**A compatibility tester for Binance Agentic Wallet dApps on BNB Smart Chain.**

Before inviting users, a dApp builder should be able to answer: *Will this
exact action reach the review screen with the right wallet, call and fee?*
VeriAbstain will compare what a dApp expects with redacted evidence from the
wallet and show what matched, differed, or remains unknown.

## First workflow

Our own receipt dApp is the first compatibility case. Its dApp browser
session exposed the regular wallet. The tester subsequently reported a
successful Binance AI Pro simulation with the expected wallet. The preview
showed no fee and returned `requireConfirmation: false`. The full calldata
comparison remains incomplete. [Pilot evidence](STATUS.md)

**Try the local compatibility checker** with the fixture modeled on the
limited AI Pro preview. Set up the [Python environment](docs/RUNNING.md#recreate-the-environment)
if needed.

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py compat --case examples\wallet-compatibility\receipt-preview-limited.json --now 1795724500
```

This fixture returns `INCOMPATIBLE`: the call matches and simulation passed.
The wallet fee is unknown, and the stated App confirmation requirement differs
from the preview. The checker runs offline. Use the
[matched and wrong-wallet examples](docs/PROJECT_SPEC.md#run-the-local-checker)
to compare all three outcomes. The [builder pilot guide](docs/COMPATIBILITY_PILOT.md)
is ready to use with an existing workflow.

### Export a shareable report

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py compat --case examples\wallet-compatibility\receipt-owner-preview.json --now 1795724572 --format markdown
```

This replays the owner's redacted historical preview at its recorded expiry.
The report records both review mismatches and leaves the overall result
`INCONCLUSIVE`. Markdown includes the public contract and expected selector.
The sender, call arguments and wallet identifiers are excluded. See the
[input and export guide](docs/PROJECT_SPEC.md#export-a-compatibility-report).

### Compare two attempts

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py compat `
  --baseline examples\wallet-compatibility\receipt-owner-developer-mode-off.json `
  --case examples\wallet-compatibility\receipt-owner-preview.json `
  --now 1795724572 --format markdown
```

The [owner's replay](docs/veriabstain-preview-assessment.md#before-and-after)
shows what changed after Developer Mode was enabled and which review
requirements remained unmet. Each result keeps its evidence label.

### Test in the browser

From the repository root, start the local workspace:

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py compat-ui
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). The saved owner
comparison opens automatically. Choose **Download Markdown** to keep a
copy. For your own cases, select a **Latest attempt** JSON file and,
optionally, an **Earlier attempt** JSON file. For a historical replay,
enter the evaluation times in UTC, then select **Run assessment**.
Files are processed in memory by the same local checker as the CLI.
Press Ctrl+C in the terminal when finished.

The public build includes a fixed, wallet-free demo under
`apps/web/dist/compatibility`. The [submission packet](docs/HACKATHON_SUBMISSION.md)
has the deployment check, form copy and demo walkthrough.

[Product specification](docs/PROJECT_SPEC.md) · [Build order](PLANS.md) · [AI handoff](AGENTS.md)

## Try the existing diagnostic

When an Agentic Wallet action gets stuck, generate a short report prompt for
`veriabstin.ai` and paste it into the AI chat where the action happened.
Review the result and save the JSON as a local file. Set up the
[Python environment](docs/RUNNING.md#recreate-the-environment) if needed.

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py diagnose --prompt
.\.venv\Scripts\python.exe tools\veriabstain.py diagnose --report wallet-issue.json
```

The diagnostic validates a limited set of fields and prints a shareable
summary labeled `USER_REPORTED`. Sharing is manual. The Agent ID is a
project label for the report. This is the evidence handoff for the proposed
compatibility tester.

## Existing receipt MVP

The published console prepares and simulates an Agent ID–gated receipt call.
The contract checks the sender's Agent ID and records two digests to attribute
an evidence review. The first live holder receipt is pending. This workflow
supplies the first compatibility case. Any future reviewer attribution is
optional for people running the compatibility check.

[Existing web console](https://agentid-web.vercel.app/) · [Web console guide](apps/web/README.md) · [Contract source on BscScan](https://bscscan.com/address/0x8ACF294c769e25dAb44aCbEb83fc401cA0702388#code) · [Finalized deployment evidence](artifacts/mvp/deployment-confirmed.json)

The Innovation Award has a separate on-chain participation threshold. Local
diagnostics and fixtures produce no qualifying interaction. [Hackathon rules](https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf)

## Test the existing components

Use the [locked Python environment](docs/RUNNING.md#recreate-the-environment) and the existing Node lockfiles under `verification/` and `verification/wallet-tests/`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/js/mvp_contract_test.cjs tests/js/mvp_deploy_browser_test.cjs tests/js/mvp_deployment_test.cjs tests/js/mvp_ui_test.cjs tests/js/provider_submit_startup_test.cjs
```

The suites cover diagnostics, evidence validation, receipt preparation and
browser wallet fixtures, plus the receipt contract on a local chain. The
original offline SDK demo is documented in the [local handoff](docs/LOCAL_HANDOFF.md).

## Research background

The original refusal-recovery comparison showed no incremental completion
benefit. EvidenceLab tied its deterministic baseline on all 62 frozen cases
and ran slower. These results inform what we reuse and still need to validate.
[EvidenceLab G3 report](docs/EVIDENCELAB_G3.md) · [Original comparison](docs/G1_EXPLORATORY_RESULT.md) · [Threat model](docs/THREAT_MODEL.md)
