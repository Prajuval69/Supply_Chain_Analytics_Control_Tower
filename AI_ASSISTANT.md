# Supply Chain Analytics Assistant

The assistant retrieves bounded structured project data through fixed, read-only SQL. It never executes generated SQL and never changes operations or sends messages. All evidence concerns fictional PackRight.

Supported intents: stockout risk, excess inventory, underperforming suppliers, OTIF failure counts, largest facility backlog, next-month forecast and critical exceptions. These cover every example question in MASTER_PROMPT.md. Unsupported questions return scope guidance instead of invented evidence.

POST `/api/assistant/query` with `{"question":"Which products have stockout risk?"}`. Return fields: `mode`, `intent`, `answer`, `evidence`, `synthetic_only`, `limitation`; optional `fallback_reason`. Evidence contains the exact retrieved metric values and IDs. Most retrievals return up to five priority records; forecasts return the three monthly totals. Explainable templates summarize evidence deterministically.

OTIF explanations count late, short and overlapping failures without claiming their operational causes. Stockout/surplus answers expose projected inventory and a rule-based action. Backlog answers rank facilities by stored quantity. Forecast answers identify target date and point estimate. Recommendations follow documented policies, not autonomous decisions.

## Optional provider

Set environment variables `LLM_API_KEY`, optional `LLM_BASE_URL` (default OpenAI-compatible `/v1`) and `LLM_MODEL`. `.env.example` is a template; the application intentionally does not auto-load `.env`. Set variables in the shell or process environment. Do not commit credentials.

Only `use_llm: true` plus a present key enables a provider call. Send the question and bounded synthetic evidence to a compatible chat-completions endpoint, with 15-second timeout and instruction to distinguish observation from causal proof. HTTP failure, malformed response or empty content returns the deterministic answer. Keys and raw provider error bodies are not logged or returned.

The no-key path and offline provider failure are tested. No live external model call was made during verification. LLM-generated prose is unverified narration even when supported evidence is attached; critical business decisions require review. The core pipeline/API needs no key, network provider or paid account.
