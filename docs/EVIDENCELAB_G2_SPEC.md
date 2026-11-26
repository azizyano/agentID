# EvidenceLab G2 corpus specification v1.0

This specification must be independently reviewed and its exact byte digest
recorded BEFORE corpus generation or candidate execution. Corrections after
freezing require a new reviewed version; never retune labels to observed output.
This is a deterministic synthetic regression corpus, not blind model evidence,
a differential baseline run, or a product-value gate. No network or chain writes.

## Semantics and representations

Scope: existing reviewed chain97 test-U allowance and commerce job status only.
No target/ABI/allowlist or candidate implementation changes in G2.

- Allowance asserts exact raw uint256 equality. Seed return100; seed claim100.
  No token-decimal conversion, inequality, quantity units or threshold operator.
- Job status asserts the known enum name. Seed job4242, enum3/COMPLETED; seed
  claimCOMPLETED. Raw tuple ID must match requested4242.
- Addresses, block hashes and byte hex digits are case-insensitive, preserving
  the `0x` prefix. JSON key order/whitespace are immaterial. Decimal numeric
  strings, lowercased status names, extra threshold/operator fields and floats
  are not alternate valid encodings under this version.
- Canonical ABI bytes are required. Golden bytes are constructed by explicit
  word layout, never by the candidate decoder/encoder or old model responses.
  SDK ABI function identity may be hashed from the pinned ABI artifact, but no
  candidate assessment/helper output may determine golden values or labels.
- All packages are SIMULATED_READ, source aliasg2-synthetic-v1. Pin metadata
  denotes the reviewed deployment definition, not actual observed chain data.

## Time and result rules

Seeds use observation1000, block timestamp990, block number40, block hash repeated
`ab`, max block age120, max observation age300 and evaluation time1000. Unless
explicitly changed, flags finalized/canonical/ABI supported aretrue, conflicts
false, errorNONE, capabilityAVAILABLE, return data present and canonical.

Expected outcomes are independent semantic labels, not candidate reason enums:

- V = VALID_AT_SNAPSHOT, I = INVALID_AT_SNAPSHOT,
  U = UNSUPPORTED_OR_INCONCLUSIVE.
- C = CURRENT, R = REVALIDATION_REQUIRED, Q = UNKNOWN.
- Unsupported schema/scope/identity/decoding declarations, conflicting or failed
  provider observations, inconsistent reproduction context, or invalid observed
  freshness cannot establish a usable temporal reference: U/Q.
- When the supported identity/declarations/context and recorded freshness are
  established, missing/undecodable return bytes leave the fact inconclusive but
  the temporal reference can still be current: U/C. It is not permission.
- Supported decoded equality means V; supported decoded inequality means I.
- Freshness at observation is separate from freshness at use. A valid observed
  snapshot retains V or I after time passes, with R rather than C.

Every case omits authorization: expected authorization_statusNOT_PROVIDED,
current_use_allowedfalse and execution_authorizedfalse. This corpus does not
test or expand recovery attempts, authorize spending or modify SDK handling.

## Frozen case recipes

Apply each following recipe independently to EACH seed, with its own rationale.
All fields not explicitly named remain unchanged. There are7controls and
24mutations per predicate: **62total cases**,14controls and48mutations.

| Recipe/category | Edit | Allowance | Job status |
| --- | --- | --- | --- |
| matched | No edit | V/C | V/C |
| address_case | Change all address hex digits to uppercase, keep0x | V/C | V/C |
| hash_hex_case | Uppercase all block/code hash hex digits, keep0x | V/C | V/C |
| calldata_hex_case | Uppercase calldata/selector/return hex digits, keep0x, in both transcript and reproduction | V/C | V/C |
| json_layout | Reverse JSON object insertion order recursively and pretty-print | V/C | V/C |
| historical_valid | Evaluation now2000, observation unchanged | V/R | V/R |
| freshness_boundary | Block timestamp880, evaluation/observation1000 | V/C | V/C |
| wrong_chain | claim.chain_id56 | U/Q | U/Q |
| wrong_contract | claim.target=0x1111111111111111111111111111111111111111 | U/Q | U/Q |
| function_mismatch | decoding.function_signature=balanceOf(address) | U/Q | U/Q |
| abi_mismatch | decoding.abi_sha256=64zero digits | U/Q | U/Q |
| unreviewed_proxy | identity.proxy_implementation=0x1111111111111111111111111111111111111111 | U/Q | U/Q |
| runtime_mismatch | identity.target_code_hash=0x+64zero digits | U/Q | U/Q |
| block_hash_mismatch | reproduction.block_hash=0x+64cd hex digits (32bytescd) | U/Q | U/Q |
| block_number_mismatch | reproduction.block_number41 | U/Q | U/Q |
| stale_at_observation | observation.block_timestamp879 (age121) | U/Q | U/Q |
| future_block | observation.block_timestamp1001 | U/Q | U/Q |
| conflicting_evidence | observation.conflictingtrue | U/Q | U/Q |
| rpc_unavailable | errorRPC_UNAVAILABLE, capabilityUNKNOWN, return_data0x | U/Q | U/Q |
| pruned_state | errorPRUNED_STATE, capabilityPRUNED, return_data0x | U/Q | U/Q |
| missing_return_data | return_data0x with otherwise supported observation | U/C | U/C |
| incorrect_assertion | claim.value101 for allowance; FUNDED for job | I/C | I/C |
| numeric_scaling | claim.value=100×10^18, raw return unchanged | I/C | U/Q |
| unsupported_threshold | Add claim.threshold=100 and claim.operator=gte | U/Q | U/Q |
| numeric_string | claim.value="100" for allowance; "3" for job | U/Q | U/Q |
| invalid_return_bytes | return_data0x01, invalid ABI length | U/C | U/C |
| calldata_argument_mismatch | Replace final calldata argument with uint2569 in both transcript/reproduction, leaving claim arguments unchanged | U/C | U/C |
| historical_incorrect_assertion | Same incorrect_assertion edit, evaluation now2000 | I/R | I/R |
| selector_mismatch | decoding.selector=0x00000000, calldata unchanged | U/Q | U/Q |
| unfinalized | observation.finalizedfalse | U/Q | U/Q |
| noncanonical | observation.canonicalfalse | U/Q | U/Q |

Numeric scaling on job status is an unsupported numeric claim, not a measured
scaling check on a status enum. Threshold cases measure explicit unsupported
semantics handling, not implemented threshold arithmetic. Conflicting evidence
cases test a recorded conflicting flag; they do not establish multi-provider
conflict detection. Those limitations must appear in the phase report.

## Corpus format and oracle

Top-level fields: corpus_kind=veriabstain.evidencelab_mutations,
corpus_version="1.0", spec_sha256, assurance=SIMULATED_READ and cases.

Each case has exactly case_id, predicate, category, control(boolean), rationale,
now(integer), input_json(string), expected. IDs use predicate/category; each
recipe has one case for each predicate. input_json preserves representation
controls. Cases are sorted lexicographically by case_id. Top-level and case
objects reject extra fields. The expected object contains exactly snapshot_status, temporal_status,
authorization_status, current_use_allowed, execution_authorized as defined above.
No candidate-specific expected reason field or model output is an oracle.

The generator must not import/call evidence_envelope, G1tests, old fixtures or
historical responses. It may load pinned SDK ABI function definitions solely
to record signature/ABI digest; golden call/return bytes are manually assembled.
Seed inputs and identity constants are public reviewed definitions.

Freeze the corpus as separate fixtures/evidencelab/g2-v1/corpus.json and SHA256
sidecar, exclusively creating files. Bind corpus to this specification's byte
digest and record generator/candidate revisions in a run artifact. Refuse
regeneration/overwrite. Checksums are local consistency anchors, not signatures.

## Execution and review

Only after independent spec review and frozen digests: parse input_json using
strict JSON, evaluate the G1candidate with frozen now and no authorization, and
compare the five semantic labels. Parsing failure means U/Q/noauthorization;
there are no intentionally malformed JSON cases in this version. Preserve every
mismatch with expected and actual labels; do not rewrite expectations to fit.

Tests must verify all62IDs, pairing,14valid controls, all categories, deterministic
regeneration in memory, checksum/spec integrity, overwrite refusal and absence
of candidate-as-oracle imports in the generator. Valid-control rejection must be
visible separately from unsupported/invalid mutation handling. No shared-control
success can be claimed as new correctness over a baseline.

Independent QA must not implement the G2generator/loader/tests it reviews.
If labels are ambiguous, record adjudication and use a new reviewed corpus
version; do not silently alter the frozenv1.0. G3baseline/differential evaluation
and metric thresholds, G4CLI/reproduction workflows, transactions, deployments,
model spending and the optional callback deadline fix remain unapproved.
