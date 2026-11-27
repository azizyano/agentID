# VeriAbstain hackathon submission

The **dApp entry** is submitted through **Submit Project Now** in the official
announcement. The deadline is **9 December 2026 at 08:00 UTC**. The X post
dated 27 November announces the community promotion award, which uses its
own form. [Official rules and project entry](https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf) · [Community X announcement](https://x.com/BinanceWallet/status/2126283464416866553)

## Project form

**1. Project name**  
VeriAbstain

**2. Project summary**  
VeriAbstain helps BNB Chain dApp builders see where an Agentic Wallet
workflow stops. It compares saved previews against the intended call and
review requirements, then produces a redacted report that shows what changed
between attempts. A deployed Agent ID–gated contract can attribute the
digests of an evidence assessment to the wallet that recorded it.

**3. Project contract**  
[VeriAbstainEvidenceRegistry on BscScan](https://bscscan.com/address/0x8ACF294c769e25dAb44aCbEb83fc401cA0702388#code).
The source-verification status is owner-reported.

**4. Website**  
[Existing receipt console](https://agentid-web.vercel.app/).
Use [the compatibility demo](https://agentid-web.vercel.app/compatibility/index.html)
after the new deployment is live and the link opens the saved comparison.

**5. Project social link**  
Paste the project’s actual X profile or its own published announcement URL.
The announcement by Binance is the source for the campaign instructions.

**6. How Agent ID is used**  
VeriAbstain’s receipt contract checks the official Agent ID registry at
recording time and rejects callers without an Agent ID. When a valid holder
records a receipt, the contract associates their wallet with two content
digests and counts the holder once. Anyone can inspect the compatibility
report before connecting a wallet. The AI Pro pilot reached simulation and
stopped because the preview omitted a displayed fee and reported
`requireConfirmation: false`; the first finalized holder receipt is still
pending.

**7. Primary Agent ID use cases**

- Identity verification
- Access control
- Agent identity binding

**8. Is the product live and available?**  
The existing receipt console is public. For an entry featuring the new
browser demo, answer **Yes** after its production URL loads the comparison.
The local workspace also supports imports and Markdown export.

**9. BNB Chain participating contract address**  
`0x8ACF294c769e25dAb44aCbEb83fc401cA0702388` on BNB Smart Chain mainnet.
This is the project’s receipt contract. There is no project token.

**10. BscScan source verification link**  
[VeriAbstainEvidenceRegistry source](https://bscscan.com/address/0x8ACF294c769e25dAb44aCbEb83fc401cA0702388#code)

**11. Completed Agent ID integration with on-chain interactions?**  
**No** as of the latest finalized read. The Agent ID check is in the deployed
contract. At block `136057025` on 27 November 2026 at 14:46:33 UTC, the
contract reported **0 receipts and 0 unique holders** (`RPC_FINALIZED_READ`).
Answer **Yes** only when a real Agent ID holder interaction is confirmed.
The Innovation Award has a separate requirement of 30 distinct Agent ID
addresses interacting with the participating contract during the submission
window. [Official award rules](https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf)

**12. Demo video**  
Record and upload the walkthrough below. Paste the viewable video link.

**13. Code repository**  
[azizyano/agentID](https://github.com/azizyano/agentID)

**14. Supplementary material**  
[Redacted pilot assessment](veriabstain-preview-assessment.md) ·
[Product specification](PROJECT_SPEC.md) ·
[Contract deployment evidence](../artifacts/mvp/deployment-confirmed.json)

## 60-second walkthrough

| Time | Show | Say |
| --- | --- | --- |
| 0–10s | Open the compatibility demo. | “VeriAbstain helps builders diagnose why an Agentic Wallet action stopped.” |
| 10–25s | Highlight Before and After, then Developer Mode and Simulation. | “In our saved pilot, the first attempt stopped before preview. The later attempt had Developer Mode enabled and simulated successfully.” |
| 25–40s | Highlight fee, App approval and exact calldata. Select Download Markdown. | “The wallet displayed no fee and reported no separate App confirmation. The exact calldata is still unknown. The report preserves those distinctions and can be shared without the raw inputs.” |
| 40–54s | Open the receipt console and show its Agent ID path and public contract link. | “The BNB Chain contract checks the official Agent ID registry at recording time. A receipt attributes two digests to the recording wallet. This pilot stopped at preview.” |
| 54–60s | Return to the report, with the project URL visible. | “Open the saved comparison in your browser. Builders can also run their own cases locally.” |

## Publish the demo using the existing Vercel project

The updated files are under `apps/web/dist/compatibility`. The Vercel
project keeps `apps/web` as its Root Directory and `dist` as its output.
The public demo serves a fixed redacted report. The Python service runs only
for local imports.

1. Review and push the project changes to your existing repository. Keep
   private evidence, credentials, and raw wallet logs out of the commit.
2. After Vercel finishes, check that
   [the demo URL](https://agentid-web.vercel.app/compatibility/index.html)
   shows the owner comparison and downloads Markdown.
3. Record the walkthrough and paste its public video link and your X URL
   into the project form. If an entry already exists, use its update path.

## Community promotion entry from the linked X post

This entry asks for the URL of an original X post about a participating
project, with both hashtags. If VeriAbstain is participating and you are
eligible for the campaign, the following is a draft for your own account:

> I built VeriAbstain after an Agentic Wallet preview passed simulation but
> left the fee and approval checks unresolved. See the before/after:
> https://agentid-web.vercel.app/compatibility/index.html
> #BinanceWalletHackathon #AgenticWallet

Publish after the demo URL works. Submit the resulting post URL through the
[official promotion form](https://www.binance.com/en/survey/ff6832f8d2984af289068c9450a3c98c).
Check the organizer’s [regional eligibility notice](https://x.com/BinanceWallet/status/2126285087927157149).
