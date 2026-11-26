# Local worker adapter

The optional Ollama adapter is implemented in `local_runtime.py`. It is not
connected to an automatic experiment runner. Importing it and running its mocked
tests makes no model calls. Runtime selection remains pending.

The adapter maps an exported comparison request to Ollama `/api/chat`, with
streaming disabled, the existing decision schema, temperature0 and512 output
tokens. See the [official chat API](https://docs.ollama.com/api/chat).
Request digest, protocol and generation settings must match. Output is imported
without repairing invalid decisions. Metadata is runtime self-report, not model
attestation. Fixture predicates remain simulated even when a real model answers.

Network transport is fixed to `http://127.0.0.1:11434/api/chat`, disables proxy
inheritance and redirects, caps response size, and never retries or downloads a
model. It sends no tools, wallet data or keys. A local server can itself forward
requests elsewhere; loopback and model-name checks do not prove local inference.
Confirm the chosen model and runtime configuration before execution.

Before real comparisons, implement a durable execution journal that reserves each
request before inference and records its output afterward. On timeout or crash,
mark effects ambiguous and reconcile; do not automatically call again. Record
model digest/configuration, adapter version, request digests, bounded call count,
and runtime observations alongside results. Preserve the existing evaluator's
UNPROVEN verdict until real C-versus-D evidence supports a gate decision.

No runtime installation, download, paid call or real inference was performed for
this adapter step. A hosted provider requires separately approved spending scope.
