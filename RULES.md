# Rule Catalogue

Canonical spec for every rule — implemented and planned. This is the source of
truth for `rationale` text in code; if you change wording here, update the
matching `Rule` subclass too.

Each entry: **what it checks** (exact AST pattern) → **fix** → **rationale**
(the exact string stored on the `Rule` class and shown in every finding).

---

## Scope boundary: hand-rolled orchestration only

Every rule below shares one unstated assumption: **the agent loop and the
retrieval pipeline are written in plain Python, in the scanned project's own
source** — a `while True:` you wrote, a `vectorstore.similarity_search()`
call you made. That assumption holds for a lot of real code — it's exactly
what let this rule set catch five genuine unbounded-retry loops in BabyAGI
and real missing-config bugs in `cafe-agent` (see the "Validated against
real code" notes throughout this file). It stops holding the moment a
project adopts a framework that owns the orchestration instead.

**Confirmed by testing against `langchain-ai/chat-langchain`** (LangChain's
own production RAG/support agent, ~2,865 lines): the scan returned **zero**
`AI_RAG_*` and **zero** `AI_AGENT_001` findings. That is not evidence the
code is unusually safe — tracing through it showed the two risks these rules
check for didn't disappear, they *relocated* to places this rule set doesn't
look:

- **The agent loop.** The app calls `define_deep_agent(tools=..., middleware=...)`
  — a LangGraph builder. LangGraph runs its own execution graph internally,
  inside the `langgraph`/`managed_deepagents` *package* — code that lives in
  an installed dependency, not in the scanned repository at all. There is no
  `while True:` anywhere in the source for `AI_AGENT_001` to find, not
  because the loop doesn't exist, but because it isn't in the part of the
  code this tool parses. The real question — is there a step/recursion cap —
  moved into whatever config is passed to the framework call.
- **The retrieval.** Documents aren't fetched into a `List[Document]` the
  orchestration code manipulates. Retrieval is one of several `@tool`-decorated
  functions (e.g. `search_support_articles(query: str) -> str`) the LLM
  decides to call at runtime; the result is a bare string folded back into
  the conversation. There is no list comprehension over retrieved objects for
  `AI_RAG_001` to inspect, because that data structure never exists in the
  orchestration code — the shape `AI_RAG_001`/`002`/`003` look for simply
  doesn't occur in this architecture.

**What this does — and doesn't — mean:**
- It does **not** mean these rules are wrong or broken. They're exactly as
  accurate on hand-rolled code as the BabyAGI/cafe-agent results show.
- It does **not** mean a framework-based agent is safe from these risks —
  only that checking for them here would require different checks entirely:
  inspecting the kwargs of a framework builder call (does it set a recursion
  limit?) and inspecting the *bodies* of `@tool`-decorated functions (do they
  return raw text with no source attribution?) instead of inspecting
  retriever call sites and raw loops.
- Closing this gap is a new, separate design effort — a LangGraph-aware
  agent-safety check and a tool-function attribution check are different
  enough in shape from the current rules that they don't belong as a patch
  to `AI_AGENT_001`/`AI_RAG_001`. Tracked as a known gap, not yet built.

---

## Implemented

### AI_LLM_001 — LLM model identifier not explicitly configured
- **Severity:** ERROR
- **Checks:** an LLM constructor call (`ChatOpenAI`, `ChatAnthropic`, etc.), a raw SDK method call (`.create()`, `.invoke()`, `.generate()`, `.run()`, `.complete()`, `.chat()`), or a bare call to a known LLM library function (`completion`/`acompletion` — LiteLLM's top-level API) — in the method and bare-function cases, only when it also carries a `messages=`/`prompt=`/`inputs=`/`input=` kwarg, missing a `model=` kwarg.
- **Fix:** pass `model="claude-sonnet-5"` (or equivalent) explicitly.
- **Rationale:** "Relying on a provider default model causes silent behavior changes when provider defaults are updated. Always pin the model name."
- **Validated against real code:** `.chat()` was added after testing against a real Ollama-based agent (`ollama.chat(model=..., messages=...)`) — the original method allowlist (`create`/`invoke`/`generate`/`run`/`complete`) missed it entirely. `completion`/`acompletion` were added after testing against BabyAGI, whose LLM calls go through LiteLLM's bare `completion(model=..., messages=...)` function rather than a method — a different call *shape* (no attribute access at all), not just a different name. The key distinction from guessing at arbitrary wrapper-function names (which is unbounded and unreliable): both additions are specific, stable, public APIs of named libraries, not a heuristic over user-chosen names. A user's own wrapper function (e.g. `gpt_call()` that internally calls `completion(...)`) isn't itself recognized — but that's fine, because the finding correctly lands on the wrapper's own definition (where `completion(...)` is actually called), which is the right place to fix it once rather than at every call site.

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
- **Checks:** a list comprehension that pulls exactly one field off each item, where that field's name is content-like — `content`, `page_content`, `text`, `chunk`, or `body` (`[d["content"] for d in docs]` or `[d.page_content for d in docs]`).
- **Fix:** keep the whole document object, or build a dict that retains `source`/`metadata`.
- **Rationale:** "Dropping metadata (source, chunk_id, score) from retrieved documents prevents downstream attribution, filtering, and debugging."
- **Validated against real code:** testing against a real scraper (`[t["title"] for t in item.get("reviewsTags", [])]`) surfaced a false positive — single-field list comprehension is an extremely common Python idiom with nothing to do with RAG. Originally the rule matched *any* field name; it's now restricted to content-like field names, since that's the actual signal distinguishing "a RAG document's text is being extracted, discarding its metadata" from "an ordinary data transform." A Subscript with a non-literal key (`d[some_var]`) is also no longer matched — the field name can't be checked statically, so it's excluded rather than guessed at.

### AI_RAG_002 — Generated answer missing source attribution
- **Severity:** WARNING
- **Checks:** a function calls the LLM, then returns a raw `response.content[0].text` (Anthropic) or `response.choices[0].message.content` (OpenAI) string with nothing else.
- **Fix:** return a structure that carries sources, e.g. `{"answer": text, "sources": [...]}`.
- **Rationale:** "RAG answers must reference their source documents so users can verify claims and so the system can be audited."

### AI_AGENT_001 — Agent workflow has no maximum step limit
- **Severity:** ERROR
- **Checks:** every literal `while True:` inside a function body (not inside a nested function/class — traversal stops at those boundaries), *except* a loop that blocks on `input()` or paces itself with a `sleep()` call somewhere in its own body.
- **Fix:** replace with `for step in range(MAX_STEPS):` or an explicit counter with a bounded exit condition.
- **Rationale:** "Unbounded agent loops (while True) can run indefinitely, exhausting tokens and budget. Define an explicit MAX_STEPS or use a bounded range loop."
- **Validated against real code (round 1 — cafe-agent):** a real interactive agent (`while True: user_input = input(...); ...; while True: response = llm.chat(...)`) exposed two bugs at once. First, the rule reported only the *first* `while True:` found per function — so the outer REPL loop (bounded, each iteration gated by a human typing) got flagged while the inner, genuinely unbounded tool-calling loop never did. That early-exit is now removed; every qualifying loop in a function is reported. Second, "bounded by a human typing" and "bounded by nothing" are different risk profiles, so a loop that blocks on `input()` anywhere in its body is now exempted.
- **Validated against real code (round 2 — BabyAGI):** testing against a real multi-agent framework surfaced the opposite kind of bug — two loops polling a third-party job-status API (`while True: status = check(...); if done: break; time.sleep(30)`) got flagged under an AI-specific rule ID with a rationale about exhausting LLM tokens, despite having no LLM call anywhere in them. Meanwhile, five *genuine* unbounded-retry loops in the same codebase (`while True: response = completion(...); try: json.loads(...); except: continue` — no backoff, retries forever on bad output) correctly kept firing. The distinguishing signal isn't "does this loop touch an LLM" (that would require resolving arbitrary cross-file wrapper functions, which isn't reliably possible); it's that a polling loop paces itself with `sleep()` and a runaway retry loop doesn't — so a loop containing `sleep()` (via `time.sleep(...)` or a bare `sleep(...)` import) is now exempted, symmetric with the `input()` check.
- **Scope note:** both exemptions check the loop's own body (not nested function/class boundaries) but do *not* stop at nested `while`/`for` boundaries — a loop with a nested inner loop that happens to call `input()` or `sleep()` somewhere deep inside would also be exempted at the outer level. Documented, not fixed, since it hasn't shown up as a real false negative yet.

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

### AI_LLM_004 — LLM call has no max_tokens limit
- **Severity:** WARNING
- **Checks:** an LLM constructor or API call (same `_is_llm_call` detection as AI_LLM_001/002) missing a `max_tokens=` or `max_completion_tokens=` kwarg.
- **Fix:** `client.messages.create(model=..., max_tokens=512, ...)`.
- **Rationale:** "Without an explicit max_tokens (or max_completion_tokens) cap, a single call's cost and latency are unbounded — a model producing an unexpectedly long response can consume far more budget than intended with no ceiling. Pin an explicit limit sized to the expected response."
- **Scope note:** this is the static-analyzable slice of "cost governance" — a per-call token ceiling. A per-session or per-user cost budget is inherently a runtime concern (it requires tracking cumulative spend across calls), not something a single-file AST pass can check; that's deliberately out of scope here.

### AI_RAG_003 — Unbounded retrieval
- **Severity:** WARNING
- **Checks:** a call to `.similarity_search(...)`, `.similarity_search_with_score(...)`, `.similarity_search_with_relevance_scores(...)`, or `.max_marginal_relevance_search(...)` with no `k=`/`top_k=` keyword argument.
- **Fix:** `vectorstore.similarity_search(query, k=5)`.
- **Rationale:** "Unbounded retrieval means an unbounded, unpredictable amount of context gets stuffed into the prompt — cost and latency vary per query with no ceiling, the same failure shape as an unbounded agent loop. Pass an explicit k= limit."
- **Scope note:** deliberately excludes a retriever's `.get_relevant_documents(...)` method — in LangChain that call takes no `k=` at the call site at all (it's configured on the retriever object via `search_kwargs`), a different detection shape not covered here. Also kwarg-only, like AI_LLM_001/002: a positional `similarity_search(query, 5)` is not flagged.

---

## Planned (not started)

The rule set covers model/temperature/max_tokens pinning, error handling, structured output, RAG metadata/attribution/retrieval limits, agent loop bounds, credentials, and prompt externalization — for hand-rolled orchestration (see "Scope boundary" above). Real candidates for what's next, in rough order of how concrete they are:

1. **Framework-aware agent safety.** Does a `define_deep_agent(...)`/LangGraph `.compile()` call set a recursion/step limit? Confirmed real gap (see "Scope boundary" above) — the most concrete item here, since we have a real repo (`chat-langchain`) that exercises it.
2. **Framework-aware RAG attribution.** Does a `@tool`-decorated function that performs a search return source-attributed results? Same real gap, different shape — needs to inspect tool-function bodies rather than retriever call sites.
3. **Prompt-injection surface.** Is untrusted user input concatenated directly into a system prompt or tool-call argument with no separation? Closer to taint analysis (tracking where a value *came from*) than pattern matching — no real-code validation yet.
4. **Audit-logging coverage.** Is every LLM call logged with enough context (prompt, response, model version, latency) to reconstruct an incident? No real-code validation yet.

None of these are a quick allowlist addition like the `.chat()`/`init_chat_model`/`completion()` fixes — each needs its own design pass before implementation, the same care the original 11 rules got.
