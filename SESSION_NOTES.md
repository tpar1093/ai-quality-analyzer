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

### Open / next session (2026-08-22, superseded below)
- ~~Add `git init` + README~~ — turned out already done by end of this session, just not noted
- Consider adding `--rule` flag to filter by rule ID (still open)
- ~~AI_PROMPT_001~~ — done, see 2026-10-02

---

## 2026-10-02

### What was covered
- Resumed after a long gap — repo was already pushed to GitHub (`tpar1093/ai-quality-analyzer`), 6f177f4 was the only commit
- Discussed and wrote `RULES.md` — the canonical spec for every rule (check logic, fix, exact rationale text), used as source of truth for the `rationale` string stored in each `Rule` class
- Built 4 new rules via strict TDD (red-green, one test at a time): `AI_SECRET_001` (hardcoded credential kwarg), `AI_PROMPT_001` (hardcoded system prompt ≥120 chars), `AI_LLM_003` (no try/except around LLM calls), `AI_RAG_003` (retriever call with no k=/top_k=) — rule set is now 10 total, 79 tests
- Added `[project.scripts]` entry point to `pyproject.toml` so the tool installs as a real `ai-quality-analyzer` command, not just `python -m analyzer`
- Added `.github/workflows/ci.yml` — runs the test suite plus a "CLI exit-code contract" smoke test (installs the package, asserts `good_app` exits 0 and `bad_app` exits non-zero) — this is the part that actually proves the packaged CLI works, which unit tests running from the source tree don't cover
- Added a README section with a copy-paste GitHub Actions snippet for someone adopting this tool in *their own* repo
- Built a demo: `DEMO.md` (interview-ready walkthrough script with talking points) and `demo.tape` (a `vhs` script — installed via `brew install vhs`, free/local/no account) that generates `demo.gif`, now embedded at the top of the README
- Created a persistent `.venv/` in the project root (gitignored already) with the package installed, used for both the CI-replica smoke testing and the demo recording

### Key design decisions
- New rules follow the existing codebase's established trade-off: function-level/kwarg-only coarse checks over deep data-flow analysis (e.g. AI_SECRET_001 doesn't trace a credential through a variable assignment; AI_LLM_003 checks "a try/except exists somewhere in the function," not that it specifically wraps the LLM call). Each has a documented "Scope note" in RULES.md rather than a silent gap.
- `RULES.md` is the spec — if rationale wording changes, update it there first, then the matching `Rule` class
- Demo GIF dimensions: 1000x620, Catppuccin Mocha theme, ~13s — tuned down from an initial 1200x780 (too much empty space, 657KB) for a tighter file (274KB)

### How to run
```bash
cd /Users/tamanna/MyProjects/ai-quality-analyzer
source .venv/bin/activate          # or: /opt/homebrew/bin/python3.11 -m venv .venv && pip install -e ".[dev]"
ai-quality-analyzer scan ./examples/bad_app
ai-quality-analyzer scan ./examples/good_app
pytest -v                          # 79 tests
vhs demo.tape                      # regenerate demo.gif after any output change
```

### Open / next session
- `--rule` flag to filter by rule ID — still on the backlog, never built
- PPT slides for presenting this as a portfolio piece — mentioned as "might have to," not started
- `RULES.md`'s "Planned" section is now empty by design; next rule candidates would need a new category (e.g. cost/token-budget checks), not gap-filling the existing ones
