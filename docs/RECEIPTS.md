# Inspect local analysis receipts

List up to100saved private receipts:

```powershell
.\.venv\Scripts\python.exe tools\receipts.py
```

Inspect one receipt using its32character ID:

```powershell
.\.venv\Scripts\python.exe tools\receipts.py --id 06146f9ac4ef47bf9fcd03aa11527780
```

`--limit` bounds listings from1to1000. Results are sorted by receipt ID, not
creation time. Commands read only the fixed private analysis-receipt directory;
they make no network/model/wallet calls and never modify records. Unexpected
names are ignored, linked receipt locations are rejected, and malformed, oversized, incomplete or duplicate-key files fail closed.

`CONTENT_CONSISTENT` means the receipt matches the supported schema and its
stored content digest. It does **not** authenticate the author, prove the chain
claim or refresh historical evidence. Reports explicitly retain
authenticated=false, truth_verified=false and execution_authorized=false.
An accepted analysis can be historical and still appear in the list.

`DIGEST_MISMATCH` detects an edit without a corresponding digest update.
`INVALID_RECEIPT` means unsupported/malformed content or unreadable/incomplete
storage. Listings return a nonzero status if any listed record is invalid; single
inspection returns0only for CONTENT_CONSISTENT. Neither status grants permission.

Schema checks reject contradictory acceptance/recommendation fields, permission
expansion, nonzero model/transaction counts, unknown assurances and raw output
fields. Summaries omit raw receipt text and unknown contents. Someone with local
write access can still rewrite a well-formed receipt and recompute its digest;
this tool cannot detect that. No signatures or on-chain registry are added.

