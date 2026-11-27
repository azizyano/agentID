# Product specification

## Active direction — Agentic Wallet compatibility tester

VeriAbstain helps BNB Chain dApp builders check a specific Agentic Wallet
workflow before inviting users. Builders provide the expected action and a
reviewed snapshot of what the wallet actually returned. A local checker
compares them and explains exactly what matched, differed, or needs evidence.
Success means a builder can resolve a real integration mismatch faster.

### Run the local checker

From the repository root, run one of the saved cases:

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py compat --case examples\wallet-compatibility\receipt-preview-matched.json --now 1795724500
```

The [matching example](../examples/wallet-compatibility/receipt-preview-matched.json)
is synthetic. The [wrong-wallet example](../examples/wallet-compatibility/receipt-wrong-wallet.json)
and [limited preview](../examples/wallet-compatibility/receipt-preview-limited.json)
are fixtures modeled on the owner’s pilot, with synthetic sender and calldata.
Use the same evaluation time for all three examples. For a current
observation, omit `--now` to use the local clock.

Provide one expected action and one observation from the same attempt. Use
whole Unix seconds for both timestamps. If the wallet provides an expiry in
milliseconds, round it down to seconds. Set the maximum observation age to
the workflow's own limit. Amounts are whole wei. Leave `wallet_fee_wei`
null when the wallet omits the fee. Record an explicit wallet-displayed zero
as numeric zero. Record `app_confirmation_required` from the wallet
response. Use `risk_findings: "clear"` only when the preview reports no
warnings. Keep omitted facts null.

The CLI returns JSON. Exit code 0 is `PREVIEW_MATCHED`. Exit code 1 returns
`INCOMPATIBLE`, `INCONCLUSIVE` or `BLOCKED_BY_WALLET`. Exit code 2 reports
invalid input without echoing it. The report retains the evidence label and
per-check results and never grants permission or verifies submission.

### First implementation

- Support one zero-value custom contract call on BNB Smart Chain mainnet
  (chain 56). The existing VeriAbstain receipt call is the first case.
- Define versioned input for the expected wallet surface, chain, public sender, contract,
  exact calldata, native value and review requirements. State whether the
  workflow needs a wallet-displayed fee and a separate Binance App confirmation.
- Accept only the observed fields needed to compare that action. Capture the
  wallet surface and observation time when available. Reuse the diagnostic
  handoff and exact receipt comparison rules where applicable. Preview
  evidence does not establish submission or finality.
- Produce deterministic, readable per-check results and a structured report.
  Identify the furthest demonstrated stage. Report mismatches explicitly.
  Missing, stale, conflicting or unsupported evidence leaves the affected
  outcome unresolved. Keep fixtures, user-reported evidence and separately
  checked public chain reads distinct.

### First acceptance cases

| Case | Expected finding |
| --- | --- |
| Complete positive fixture | Preview fields and review requirements match. Submission is unverified. |
| dApp browser exposes the regular wallet | Sender differs from the expected Agentic Wallet. |
| Exact call simulates with no App approval and no wallet-displayed fee | Simulation passes. The stated App approval requirement is unmet and fee display is unverified. |
| Calldata, destination, chain, or native value differs | Action mismatch even if the wallet simulated successfully. |
| Preview is expired, missing required facts, blocked, or contradictory | Identify the observed limit or block and leave any unsupported outcome unresolved. |

The CLI runs locally on saved examples. It accepts no credentials or raw
wallet logs and performs no wallet action, transaction, retry, or deployment.
Reports describe observed compatibility for the given action and evidence.
They confer no certification, blanket safety verdict, or permission to
execute. Agent ID can later attribute a report to its reviewer if users need
that. Running the compatibility check does not require Agent ID.

After the local cases pass, compare the report with one external builder's
existing, redacted example. Measure time and correctness against their usual
Binance and explorer checks. Ask before building a new UI or starting
outreach. See the [ordered build](../PLANS.md) and [pilot guide](COMPATIBILITY_PILOT.md).

## Original research brief

### Initial task

An authorized ERC-8183 worker analyzes a particular BSC ERC-20 allowance or selected job state and produces structured factual output. A controlled external tool response may contain a false warning. VeriAbstain assesses the warning without granting new actions.

Sequence: capture observable refusal and provenance; extract a supported typed claim; resolve a pinned block; verify the predicate; report verdict and assurance; recheck original authorization; permit at most one bounded reconsideration; validate the deliverable before ordinary SDK submission; retain a privacy-aware receipt.

### Non-goals

No arbitrary proof of AI correctness, general transaction-safety verdict, safety oracle, validator network, SDK replacement, asset custody, wallet pairing service, automatic approvals/transfers, or fabricated adoption. No general prompt-injection immunity claim.

### Acceptance

G1 must demonstrate incremental benefit over a correctly prompted worker with a trusted direct read. A fixture-only result cannot establish model behavior. Real job/model prerequisites and measured costs must be recorded. Zero observed unauthorized or duplicate effects is a test result, not a universal security guarantee.

### Event constraints

The [official announcement](https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf) gives the submission window as 18 November 2026 08:00 UTC through 9 December 2026 08:00 UTC. Innovation Award eligibility requires a live product and at least 30 interacting Agent ID holder addresses during that window. Participating contracts must be deployed on BNB Chain, source-verified, and open-source. These requirements remain unfulfilled.
