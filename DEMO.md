# Live Demo Script

A ~3-minute walkthrough for interviews / screen-shares. Each step has what to
say and the exact command to run. Activate the project venv first:

```bash
source .venv/bin/activate
```

---

### 1. Set up the premise (30s)

> "This is a static analyzer for LLM and RAG applications — the same idea as
> MISRA or Model Advisor in automotive, applied to AI code instead. It parses
> Python with the `ast` module and looks for silent defaults and governance
> gaps that a normal linter has no concept of — things like 'is this model
> pinned' or 'does this agent loop have a stop condition.'"

Open `examples/bad_app/rag_app.py` and scroll through it.

> "At a glance this looks like completely normal RAG code — client, retrieve,
> answer, an agent loop. Nothing here would trip a linter or a type checker."

### 2. Run the scanner (30s)

```bash
ai-quality-analyzer scan ./examples/bad_app
```

> "Eleven findings. Each one has a rule ID, a severity, the exact file and line,
> and — this is the part I care about — a rationale. Not just 'this is bad,'
> but *why* it's a problem: [pick one, e.g. the hardcoded API key] a literal
> credential gets baked into git history permanently, and rotating the key
> afterwards doesn't undo that."

### 3. Fix one live (45s) — the most convincing moment

Open the file, find the `client.messages.create(...)` call missing `model=`.
Add it:

```python
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=256,
    ...
)
```

Rerun:

```bash
ai-quality-analyzer scan ./examples/bad_app
```

> "Down to ten findings — AI_LLM_001 is gone. This is meant to run as a
> pre-commit or CI step, catching exactly this kind of thing before it ships."

### 4. Show the compliant version (20s)

```bash
ai-quality-analyzer scan ./examples/good_app
```

> "Same application, rewritten to satisfy every rule. Zero findings, exit
> code 0."

### 5. Prove it survives contact with real code (45s) — the credibility moment

> "Toy examples prove a rule *can* fire. They don't prove it fires
> *correctly*. So I ran this against real projects I didn't write."

Open `RULES.md`, scroll to a "Validated against real code" note (e.g. under
`AI_AGENT_001`).

> "Testing against my own cafe-agent project found a real blind spot — Ollama's
> `.chat()` call wasn't in the method allowlist, so four rules missed it
> entirely. Testing against BabyAGI, a well-known open-source agent framework,
> found the opposite problem: the agent-loop rule flagged an HTTP job-polling
> loop that had nothing to do with LLMs at all, while five *genuine* unbounded
> retry loops in the same codebase correctly kept firing. Both are documented
> and fixed, with the real code that exposed them, right in the spec."

### 6. Show it's already wired into CI (30s)

Open `.github/workflows/ci.yml` or the Actions tab on GitHub.

> "It's not just a CLI toy — exit code 1 on any finding is already gating
> pull requests on this repo. Anyone adopting this in their own project drops
> in about six lines of YAML — it's in the README."

### 7. Mention the design, if asked (30s)

> "Zero runtime dependencies — stdlib only, `ast`/`argparse`/`json`. Every
> rule is an independent class with a `check(tree, filepath) -> list[Finding]`
> interface, so adding a new rule never touches the scanner or CLI. The full
> rule spec — what each one checks, the fix, the exact rationale — lives in
> `RULES.md`."

---

## Fallback one-liner (no setup, elevator-pitch version)

```bash
ai-quality-analyzer scan ./examples/bad_app && echo CLEAN || echo "11 findings — see above"
```
