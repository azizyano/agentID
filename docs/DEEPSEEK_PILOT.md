# DeepSeek pilot

Owner authorized DeepSeek comparisons with a total maximum of $2 on2026-11-20.
The key pasted in chat must be revoked and replaced. Never put a replacement in
chat, command arguments, a tracked file, or an assistant tool call.

From a normal local PowerShell terminal in this repository:

```powershell
.\.venv\Scripts\python.exe tools\run_deepseek_batch.py --requests artifacts/g1b/requests.jsonl
.\.venv\Scripts\python.exe tools\run_deepseek_batch.py --requests artifacts/g1b/requests.jsonl --execute
```

First command validates five requests without calls. Second prompts for the NEW
key with hidden input and runs at most five requests. The key remains process
memory only. Input fails closed if hidden entry is unavailable. Assistant never
reads it. Console output omits provider exception details and response bodies.

The pilot selects `deepseek-flash`, non-thinking mode, temperature0,512 maximum
output tokens and JSON output. Existing request schema is appended identically
for every arm. Actual payload digest and provider-reported usage/model are
recorded; aliases can change underlying models. Sources checked2026-11-20:
[API](https://api-docs.deepseek.com/api/create-chat-completion/) and
[pricing](https://api-docs.deepseek.com/quick_start/pricing/).

Shared ledger: `artifacts/private/deepseek/budget.sqlite3`. Every attempted call
reserves $0.02 BEFORE transmission, including failed/ambiguous calls, against
$2 total. Five new calls reserve at most $0.10. Under reviewed maximum rates of
$0.30/M input and $1.20/M output tokens, the bounded payload plus4096 token
overhead and512 output tokens fit the reservation. This is a conservative local
budget, not a provider-enforced billing limit. Price changes, other programs,
or deleted/copied ledgers are outside its enforcement. Do not delete/copy the
ledger or run another paid runner to reset spending. Actual provider billing
remains authoritative. Stop if usage/rates differ from reviewed assumptions.

On resume, completed requests are returned from the ledger without another
model call; ambiguous requests stop. The pilot always uses the first five
exported requests. It does not automatically run the full200-request set or
claim paired behavioral success. At $0.02 reserved per attempt this ledger
allows at most100 attempted calls; a full experiment needs a tighter reviewed
bound or a smaller preregistered scope, never a silent cap increase.

Output is `artifacts/private/deepseek/responses.jsonl`. Metadata and completed
responses remain durable in SQLite. A failure can leave partial durable results;
do not automatically retry or erase state. Imports still use the existing
unattested replay evaluator; provider observations do not prove product value.
Only fixture request messages/schema are sent, no wallet secrets, evaluator
expected answers, chain writes, tools, or confidential user prompts.

## Prepared exploratory paired phase

The frozen `artifacts/private/deepseek/paired-plan.json` selects16scenarios,
all10conditions and both predicates, for C/C_RETRY/D. It reuses prior answers.
This exploratory subset cannot satisfy the full G1 gate. First round48requests;
at most32qualified reconsiderations later. Maximum additional reservation$1.60,
plus prior$0.10, stays below$2. No prompt/schema/outcome edits were made.

```powershell
.\.venv\Scripts\python.exe tools\run_deepseek_batch.py --requests artifacts/private/deepseek/paired-requests.jsonl --limit 48 --execute
```

Enter replacement key at hidden prompt. This may take several minutes; run once.
Completed calls persist immediately. Exports now accumulate all completed ledger
responses, preserving pilot answers; never overwrite the ledger to reset spend.
No automatic reconsideration or later batch is launched. Return only final status.
