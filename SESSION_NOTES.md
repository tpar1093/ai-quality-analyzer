# Session Notes

---

## 2026-08-22

### What was covered
- Built `ai-quality-analyzer` from scratch — a portfolio project inspired by MXAM/Model Advisor
- Static analysis tool for LLM/RAG Python applications using Python's built-in `ast` module
- Implemented 6 rules: AI_LLM_001, AI_LLM_002, AI_OUTPUT_001, AI_RAG_001, AI_RAG_002, AI_AGENT_001
- Built CLI, terminal + JSON reporters, example bad_app (violates all rules) and good_app (zero findings)
- 56 pytest tests, all passing. Zero runtime dependencies (stdlib only)

### Key design decisions
- Rules are classes inheriting from `Rule(ABC)` with a `check(tree, filepath) -> list[Finding]` interface
- `_walk_no_nested_fns()` helper prevents false positives by stopping AST traversal at nested function/class boundaries
- AST-based detection is more robust than regex: correctly handles LangChain constructors vs raw Anthropic SDK calls
- `python3.11` from Homebrew is needed (system Python is 3.9, incompatible with `X | Y` union syntax)

### How to run
```bash
cd /Users/tamanna/MyProjects/ai-quality-analyzer
/opt/homebrew/bin/python3.11 -m analyzer scan ./examples/bad_app
/opt/homebrew/bin/python3.11 -m analyzer scan ./examples/bad_app --format json
/opt/homebrew/bin/python3.11 -m pytest -v
```

### Open / next session
- Add `git init` + README so it's ready to push to GitHub as a portfolio piece
- Consider adding `--rule` flag to filter by rule ID
- Possible next rule: AI_PROMPT_001 — system prompt must be externalized (not hardcoded inline)
