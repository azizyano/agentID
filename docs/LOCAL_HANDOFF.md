# Local utility handoff

The owner-approved narrower read-only validation utility is implemented and
locally runnable. No user test run, wallet action or API key is needed to finish
this handoff. This is not a production release or the original G1 value gate.

## One entry command

From the repository folder, using the installed Python3.12 environment:

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py doctor
.\.venv\Scripts\python.exe tools\veriabstain.py demo
.\.venv\Scripts\python.exe tools\veriabstain.py receipts
```

`doctor` checks installed prerequisite package versions and the frozen fixture
manifest checksum offline. LOCAL_SETUP_READY is not source attestation, a live
RPC test or production readiness. `demo` runs actual SDK verification against
synthetic chain/worker data and checks redelivery. `receipts` checks historical
local record shapes/digests without authenticating them.

For a separately authorized real analysis:

```powershell
.\.venv\Scripts\python.exe tools\veriabstain.py check --authorization path/to/current-authorization.json --analysis path/to/analysis.json
.\.venv\Scripts\python.exe tools\veriabstain.py receipts --id RECEIPT_ID
```

The `check` command independently reads the supplied analysis's finalized block,
restricted to reviewed chain97 targets; validates scope, deadline, freshness,
runtime/ABI, block and value; and atomically saves a private receipt. Acceptance
does not authorize submission. No model runs, wallet operations, uploads or
automatic retries are part of this command. Help is available per command.

## Completed evidence

- Full regression suite313passed,0failed/skipped; one existing dependency warning.
  JUnit: `artifacts/local-handoff-tests.xml`.
- Actual SDK watcher/callback composition with independent evidence interface,
  strict grading and shared durable single-analysis journal is fixture-tested.
- Public testnet reads separately confirmed allowance0 and completed job1766.
  Real CLI smoke accepted a matching manually asserted value and rejected a
  wrong value; both private receipts passed offline consistency inspection.
- Earlier user-signed testnet lifecycle job1766 completed and paid1testU.
  No new job was created for this utility.
- Earlier DeepSeek exploratory subset did not show D improving completion over
  C; original G1no-go remains.55calls recorded, $1.10conservatively reserved of
  $2; provider invoice unknown. No paid continuation is attached to this CLI.

## Boundaries

Single-provider finalized RPC reads are labeled RPC_FINALIZED_READ. They are not
cryptographic proofs. Local record digests are content checks, not signatures or
immutable storage. Authenticated authorization, clock, storage and independent
job binding remain caller responsibilities. Saved acceptance is historical;
fresh evidence/SDK checks would be needed for any separate future submission.

This handoff does not include a UI/API, production auto-submission/recovery,
new receipt contract, mainnet deployment, arbitrary chain/token support or
demonstrated differentiated product value. Those require separate scope/value
review. The completed utility needs no further wallet or paid model actions.

Detailed guides: [command](CHECK_ANALYSIS.md), [receipts](RECEIPTS.md),
[SDK callback](APPLICATION_CALLBACK.md), [evidence](CHAIN_EVIDENCE.md),
[validation](DELIVERABLE_VALIDATION.md), [experiment result](G1_EXPLORATORY_RESULT.md).
