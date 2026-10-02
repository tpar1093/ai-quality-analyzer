# Rule Catalogue

Canonical spec for every rule — implemented and planned. This is the source of
truth for `rationale` text in code; if you change wording here, update the
matching `Rule` subclass too.

Each entry: **what it checks** (exact AST pattern) → **fix** → **rationale**
(the exact string stored on the `Rule` class and shown in every finding).

---

## Implemented

### AI_LLM_001 — LLM model identifier not explicitly configured
- **Severity:** ERROR
- **Checks:** an LLM constructor call (`ChatOpenAI`, `ChatAnthropic`, etc.) or a raw SDK call with a `messages=`/`prompt=` kwarg, missing a `model=` kwarg.
- **Fix:** pass `model="claude-sonnet-5"` (or equivalent) explicitly.
- **Rationale:** "Relying on a provider default model causes silent behavior changes when provider defaults are updated. Always pin the model name."

### AI_LLM_002 — LLM temperature not explicitly configured
- **Severity:** WARNING
- **Checks:** same LLM-call detection as AI_LLM_001, missing `temperature=`.
- **Fix:** pass `temperature=0.2` explicitly.
- **Rationale:** "Provider defaults for temperature vary and change over time. Explicit configuration ensures reproducible, predictable outputs."

### AI_OUTPUT_001 — Machine-consumed LLM output lacks structured schema
- **Severity:** WARNING
- **Checks:** a function makes an LLM call but contains no `json.loads(...)`, `response_format=` kwarg, or `.with_structured_output(...)` anywhere in its body.
- **Fix:** parse with `response_format={"type": "json_object"}` or a Pydantic schema via `.with_structured_output(...)`.
- **Rationale:** "LLM output consumed by code should be validated against a schema (json.loads, Pydantic, or response_format). Raw strings break silently when the model changes its output format."

### AI_RAG_001 — Retrieved documents strip source metadata
- **Severity:** ERROR
- **Checks:** a list comprehension that pulls exactly one field off each item (`[d["content"] for d in docs]` or `[d.page_content for d in docs]`).
- **Fix:** keep the whole document object, or build a dict that retains `source`/`metadata`.
- **Rationale:** "Dropping metadata (source, chunk_id, score) from retrieved documents prevents downstream attribution, filtering, and debugging."

### AI_RAG_002 — Generated answer missing source attribution
- **Severity:** WARNING
- **Checks:** a function calls the LLM, then returns a raw `response.content[0].text` (Anthropic) or `response.choices[0].message.content` (OpenAI) string with nothing else.
- **Fix:** return a structure that carries sources, e.g. `{"answer": text, "sources": [...]}`.
- **Rationale:** "RAG answers must reference their source documents so users can verify claims and so the system can be audited."

### AI_AGENT_001 — Agent workflow has no maximum step limit
- **Severity:** ERROR
- **Checks:** a literal `while True:` inside a function body (not inside a nested function/class — traversal stops at those boundaries).
- **Fix:** replace with `for step in range(MAX_STEPS):` or an explicit counter with a bounded exit condition.
- **Rationale:** "Unbounded agent loops (while True) can run indefinitely, exhausting tokens and budget. Define an explicit MAX_STEPS or use a bounded range loop."

---

### AI_SECRET_001 — Credential passed as a hardcoded string literal
- **Severity:** ERROR
- **Checks:** a call keyword argument named `api_key`, `auth_token`, `access_token`, `secret`, `secret_key`, or `password`, whose value is a non-empty string literal (`ast.Constant`) rather than an expression (`os.getenv(...)`, `os.environ[...]`, a variable reference, etc.).
- **Fix:** `Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))` — load from environment or a secret manager at runtime.
- **Rationale:** "A literal string value is written into the source file and therefore into git history permanently — removing it in a later commit does not purge it from history, and rotating the credential does not revoke access for anyone who already cloned or mirrored the repository. Load credentials at runtime via an environment variable or a secret manager, never as a literal in code."
- **Scope note:** only flags a literal directly in the call. A variable that itself holds a hardcoded string one assignment away (`API_KEY = "sk-..."; client = Anthropic(api_key=API_KEY)`) is not traced — that would need cross-statement data-flow analysis, out of scope for a single-pass per-call AST rule. Worth flagging as a known gap, not silently.

### AI_PROMPT_001 — System prompt is hardcoded inline rather than externalized
- **Severity:** WARNING
- **Checks:** either (a) a `system=` call kwarg, or (b) a `{"role": "system", "content": ...}` dict literal (OpenAI chat format) — in both cases where the content value is a string/f-string literal at least `MIN_LENGTH` (120) characters long.
- **Fix:** move the text to `prompts/system.txt` (or a `prompts.py` constants module) and load it at call time.
- **Rationale:** "System prompts are edited far more often than application logic — by prompt engineers, during A/B tests, or in response to model behavior changes — and a prompt embedded directly in a function call has no version history independent of the surrounding code, cannot be diffed or rolled back on its own, and forces a full code review and deploy for a wording change. Externalize it to a dedicated file or a prompts module loaded at runtime."
- **Scope note:** the 120-char threshold is a deliberate false-positive guard — a one-line `system="You are a helpful assistant."` isn't a governance problem worth flagging; a growing prompt block is. Threshold is a class constant, easy to tune later.

### AI_LLM_003 — No error handling around LLM calls
- **Severity:** WARNING
- **Checks:** a function that contains an LLM API call, but contains no `ast.Try` node anywhere in its own body (nested functions excluded).
- **Fix:** wrap the call in `try/except (RateLimitError, APITimeoutError, APIError)`.
- **Rationale:** "LLM APIs fail more often and in more varied ways than typical REST calls — rate limits, timeouts, content filtering — and an uncaught exception from a single LLM call takes down the entire request path around it. Wrap the call in a try/except for the provider's error types."
- **Scope note:** function-level, like AI_OUTPUT_001 and AI_RAG_002 — it checks that *a* try/except exists somewhere in the function, not that it specifically wraps the LLM call. A `try/except` guarding an unrelated line would satisfy the check. Same class of simplification the rest of this codebase already accepts for low false-positive-rate heuristics.

### AI_RAG_003 — Unbounded retrieval
- **Severity:** WARNING
- **Checks:** a call to `.similarity_search(...)`, `.similarity_search_with_score(...)`, `.similarity_search_with_relevance_scores(...)`, or `.max_marginal_relevance_search(...)` with no `k=`/`top_k=` keyword argument.
- **Fix:** `vectorstore.similarity_search(query, k=5)`.
- **Rationale:** "Unbounded retrieval means an unbounded, unpredictable amount of context gets stuffed into the prompt — cost and latency vary per query with no ceiling, the same failure shape as an unbounded agent loop. Pass an explicit k= limit."
- **Scope note:** deliberately excludes a retriever's `.get_relevant_documents(...)` method — in LangChain that call takes no `k=` at the call site at all (it's configured on the retriever object via `search_kwargs`), a different detection shape not covered here. Also kwarg-only, like AI_LLM_001/002: a positional `similarity_search(query, 5)` is not flagged.

---

## Planned (not started)

Nothing currently queued — the rule set now covers model/temperature pinning, error handling, structured output, RAG metadata/attribution/retrieval limits, agent loop bounds, credentials, and prompt externalization. Next candidates would come from a new category (e.g. cost/token-budget checks) rather than filling gaps in the existing ones.
