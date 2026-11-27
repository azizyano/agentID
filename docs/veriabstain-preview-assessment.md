# VeriAbstain preview assessment

**Record an assessment on BNB Smart Chain using Binance AI Pro.**
The historical preview reportedly simulated successfully. The workflow
required a displayed network fee and a separate Binance App approval.
The preview showed no fee and reported `requireConfirmation: false`.

| Check | Reported evidence |
| --- | --- |
| Evidence source | `USER_REPORTED`. The tester’s earlier detailed summary of the Binance AI Pro preview. |
| Sender | The summary reports that the selected wallet matched the expected sender. |
| Chain | BNB Smart Chain, chain ID 56. |
| Target | `0x8ACF294c769e25dAb44aCbEb83fc401cA0702388`. |
| Native value | 0 wei. |
| Simulation | Passed, code `000000000`. |
| Risk findings | The summary reports none in the preview. |
| Network fee | No fee was displayed. The amount is unknown. |
| App approval flag | `requireConfirmation: false`. The workflow required `true`. |
| Exact calldata match | Incomplete. Full original `--inputData` and full wallet-returned calldata are unavailable. |
| Timing | Exact observation time unknown. Reported preview expiry was 2026-11-26 20:22:52 UTC. The VeriAbstain snapshot expired at 20:22:06 UTC that day. |
| Submission | The tester reports that the flow stopped at the preview. No transaction hash was reported. |

This assessment applies to that preview and has expired with it. The evidence
is sufficient to identify the review requirements the preview did not meet.
It is incomplete for a strict compatibility verdict. The sender address
and request identifiers are omitted from this shareable copy.

## Before and after

The tester first reported that Binance AI Pro selected their wallet and
stopped before preview because Developer Mode was disabled. The later
summary reported Developer Mode enabled and a successful simulation.

| Check | Before | After |
| --- | --- | --- |
| Developer Mode | Disabled | Enabled |
| Simulation | No preview | Passed |
| Fee display | Unknown | Required fee was absent |
| Separate App approval | Unknown | Required flag was false |
| Exact calldata | Unknown | Unknown |

The saved cases are [before](../examples/wallet-compatibility/receipt-owner-developer-mode-off.json)
and [after](../examples/wallet-compatibility/receipt-owner-preview.json).
The attempt order comes from the tester’s reports. The exact observation
times and full calldata remain unavailable, so both assessments are
`INCONCLUSIVE`. This records a precheck blocker cleared and two review
requirements still unmet.
