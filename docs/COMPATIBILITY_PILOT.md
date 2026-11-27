# First Agentic Wallet compatibility pilot

Use one builder's existing preview or wallet-selection observation for one
zero-value BNB Smart Chain custom call. The pilot compares the builder's usual
review with VeriAbstain and records whether they reached the right conclusion
faster. The builder can run the checker locally with saved evidence.

## Invite a builder

> Have you already tried one zero-value BNB Smart Chain action from Binance
> Agentic Wallet? I'm testing a local compatibility tool that compares what
> your dApp expected with what the wallet showed. Could we replay one existing
> preview and compare it with how you diagnosed it? No new wallet request or
> transaction is needed. You can keep the input on your computer and share
> only the check results.

Use only an existing workflow with the builder's permission. Skip token
approvals, trading flows, message signing, and cases that need a new wallet
connection or a live retry.

## Prepare one case

Start from the [matching example](../examples/wallet-compatibility/receipt-preview-matched.json).
Save the new case locally in a private location outside version control.
Replace the example fields with the builder's documented action and one
redacted observation from the same attempt:

- **Expected action.** Specify the wallet surface, chain, public sender, target,
  exact calldata and native value from the plan. Record in advance whether the
  flow requires the wallet to show a fee and a separate Binance App approval.
  Use the workflow's original freshness limit.
- **Observed action.** Set the evidence label to `USER_REPORTED`. Copy only the
  fields the builder can confirm, such as selected sender, reported stage,
  observed chain and call, wallet fee, App confirmation flag and risk findings.
  Use null for missing fields. A receipt or a gas estimate from a different
  attempt cannot fill a gap in this preview.
- **Time.** Use the original observation and expiry times in whole Unix
  seconds. For a historical replay, pass the real time at which the preview was
  reviewed using `--now`. Leave uncertain timestamps null. Keep replay results
  tied to their historical context.

Keep keys, pairing and session data, request and order IDs, private arguments,
and full logs out of the case. If the exact input is confidential, the builder
can compare it on their own machine and share only the generated report.

## Compare both workflows

1. Ask the builder to walk through their usual Binance, dApp, or explorer
   checks from the same saved evidence. Record what they conclude about the
   sender, action match, fee, App confirmation and submission. Record the
   elapsed time and which questions remain unresolved.
2. Run the existing checker against the same case.

   ```powershell
   .\.venv\Scripts\python.exe tools\veriabstain.py compat --case PATH_TO_REDACTED_CASE.json --now UNIX_SECONDS_AT_REVIEW
   ```

   Record its elapsed time from reading the input through interpreting the
   report. Include time spent assembling its JSON. Exit code 1 is a report
   outcome. Exit code 2 is invalid input.
3. Verify both sets of answers against the same original observation. Count a
   saved step or a correctly identified mismatch the builder would otherwise
   miss. Note whether running the ordinary review first helped the builder with
   the checker. Leave disagreements unresolved unless supported by evidence.

Share only the per-check result, source class, surface, timing, and one sentence
on what changed for the builder. Useful evidence includes a missed mismatch
caught by the checker or a faster correct answer after accounting for input
preparation. One pilot can inform the next change. It cannot establish
general compatibility, adoption, or an on-chain interaction.
