# Worker comparison protocol v1

Implemented as offline request/response adapters. No model runtime is selected or invoked. Results are always labelled FIXTURE_REPLAY_UNATTESTED; importing a response file does not establish model provenance or real-chain integration.

## Export

```powershell
.\.venv\Scripts\python.exe tools\run_comparison.py
```

This creates 200 first-round requests: 40 frozen scenarios x A, B, C, C_RETRY, D. Schedule seed is 20261119. Files and resumable SQLite state live under `artifacts/g1b/`. Only unanswered requests appear in `requests.jsonl`; completed observations remain in the local state and results.

CLI exits 2 while awaiting replies, 0 after replay processing, and 1 on errors. Reports publish through atomic file replacement; `summary.json` is the final commit marker. A RUNNING/ERROR report has `artifacts_complete=false` and must not be treated as a completed export. Error cleanup preserves the ledger and invalidates generated request/result files.

Every request has an opaque `request_id`, a `request_digest`, and a `request` containing messages, output JSON Schema, and equal per-call generation settings. Condition labels, fixture IDs, and expected answers are excluded from model messages. Never send the evaluator's `results.jsonl` or full fixture manifest as model context.

## Arms

- A: ordinary analysis instructions and the untrusted scanner observation.
- B: A plus verify-before-refusal instructions, without a supplied trusted direct read.
- C: correct verification instructions and the trusted direct read.
- C_RETRY: identical first prompt/read to C; one additional reconsideration after refusal, subject to unchanged authorization and effect reconciliation.
- D: the same direct read plus a typed assessment. One reconsideration only if the worker explicitly refuses on a matching factual claim, that claim is contradicted, authorization still holds, and no prior/ambiguous effect exists.

C/C_RETRY/D receive identical underlying facts. C_RETRY controls for the additional attempt; D does not receive additional facts on retry. Common safeguards validate outputs and original authorization for every arm. These controls must be included when interpreting any eventual difference in completions.

## Import

A later runtime adapter must consume only exported request bodies, pin the model/settings, record actual usage/latency, and return JSONL records with exactly these string fields:

```json
{"request_id":"exported ID","request_digest":"exported digest","output":"JSON matching the exported response_schema"}
```

Import the file without calling a model:

```powershell
.\.venv\Scripts\python.exe tools\run_comparison.py --responses recorded-responses.jsonl
```

Rerunning resumes the same operation/request IDs. Valid qualified refusals may export a second request. At most two request slots exist for each scenario/arm. A second refusal ends the attempt. Changing original context, conflicting recorded responses, duplicate response IDs, unexpected fields, nonstandard JSON, and mismatched request digests fail closed. Missing responses stay pending.

Stored requests are bound to their operation, round, canonical body, and digest before a cached reply is returned. SQLite write reservations serialize competing updates. Saved payload/response consistency is checked on resume. These checks detect inconsistent local data; hashes do not authenticate a database against someone who can rewrite both content and digests. No external model-call lease or transaction reconciliation is implemented.

Do not erase state or change run IDs to bypass an attempt budget. Independent pre-registered repetitions use distinct run IDs and are separate experiments. The SQLite store is an experiment ledger, not a production submission/recovery journal; no external transaction is performed.

## Scope of the current evidence

The tests use explicitly scripted response doubles to test adapter behavior. They do not demonstrate an AI failure or improvement over C. Accepted analysis means a simulated factual deliverable passed objective grading. It does not authorize an asset action. Genuine warnings can be reported successfully; unsupported/stale/failed facts cannot become accepted deliverables.

Real worker execution, model provenance/usage accounting, three repetitions, local funded-job integration, and the G1 value gate remain pending. Runtime choice was explicitly deferred by the owner. No paid model calls are authorized by exporting these files.
