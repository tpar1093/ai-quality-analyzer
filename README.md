# ai-quality-analyzer

[![CI](https://github.com/tpar1093/ai-quality-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/tpar1093/ai-quality-analyzer/actions/workflows/ci.yml)

Static analysis for LLM and RAG applications — rule-based quality checking inspired by automotive tools like MXAM and Model Advisor.

Scans Python source files using AST analysis and reports violations as structured findings with rule ID, severity, rationale, and location.

![Demo: scanning a non-compliant RAG app finds 11 issues; the compliant version passes clean](demo.gif)

---

## Rules

| Rule ID | Title | Severity |
|---|---|---|
| `AI_LLM_001` | LLM model identifier not explicitly configured | ERROR |
| `AI_LLM_002` | LLM temperature not explicitly configured | WARNING |
| `AI_LLM_003` | No error handling around LLM calls | WARNING |
| `AI_LLM_004` | LLM call has no max_tokens limit | WARNING |
| `AI_OUTPUT_001` | Machine-consumed LLM output lacks structured schema | WARNING |
| `AI_RAG_001` | Retrieved documents strip source metadata | ERROR |
| `AI_RAG_002` | Generated answer missing source attribution | WARNING |
| `AI_RAG_003` | Unbounded retrieval (no k= limit) | WARNING |
| `AI_AGENT_001` | Agent workflow has no maximum step limit | ERROR |
| `AI_SECRET_001` | Credential passed as a hardcoded string literal | ERROR |
| `AI_PROMPT_001` | System prompt is hardcoded inline rather than externalized | WARNING |

Full spec for every rule (what it checks, the fix, the exact rationale) lives in [`RULES.md`](RULES.md).

---

## Usage

```bash
# Scan a directory — terminal output
python -m analyzer scan ./my_app

# Scan a single file
python -m analyzer scan ./my_app/rag.py

# JSON output (for CI or tooling integration)
python -m analyzer scan ./my_app --format json

# Run only specific rules (repeat --rule for more than one)
python -m analyzer scan ./my_app --rule AI_SECRET_001 --rule AI_PROMPT_001
```

Exit code `0` = no findings. Exit code `1` = findings found. Suitable for use in CI pipelines. An unrecognized `--rule` ID exits `2` and lists the valid IDs.

---

## Using it as a CI gate in your own project

Install it as a dependency, then run it as a step in your pipeline — it fails the build on any finding via its exit code, the same contract this repo's own [`ci.yml`](.github/workflows/ci.yml) relies on.

```yaml
# .github/workflows/ai-quality.yml
name: AI Quality Gate

on: [pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install git+https://github.com/tpar1093/ai-quality-analyzer.git
      - run: ai-quality-analyzer scan ./src
```

Swap `./src` for the path to your actual application code. A pre-commit hook is a lighter-weight alternative (catches issues before the commit even lands), but it's skippable with `--no-verify` — CI is the version nobody can bypass.

---

## Example

Running against the included bad example app:

```
python -m analyzer scan ./examples/bad_app
```

```
[ERROR] AI_LLM_001: LLM model identifier not explicitly configured
  Location : examples/bad_app/rag_app.py:49
  Finding  : LLM call is missing required 'model=' argument.
  Rationale: Relying on a provider default model causes silent behavior changes
             when provider defaults are updated. Always pin the model name.

[WARNING] AI_LLM_002: LLM temperature not explicitly configured
  ...

[WARNING] AI_LLM_003: No error handling around LLM calls
  ...

[WARNING] AI_LLM_004: LLM call has no max_tokens limit
  ...

[ERROR] AI_RAG_001: Retrieved documents strip source metadata
  Location : examples/bad_app/rag_app.py:40
  Finding  : List comprehension over 'raw_docs' discards document metadata.
  ...

[WARNING] AI_RAG_003: Unbounded retrieval
  ...

Total: 11 finding(s)
```

The `examples/good_app/` version of the same application passes all checks.

---

## Architecture

```
analyzer/
├── rules/
│   ├── base.py          # Finding dataclass, Rule ABC, AST walk helper
│   ├── llm_rules.py     # AI_LLM_001, AI_LLM_002, AI_LLM_003, AI_LLM_004
│   ├── output_rules.py  # AI_OUTPUT_001
│   ├── rag_rules.py     # AI_RAG_001, AI_RAG_002, AI_RAG_003
│   ├── agent_rules.py   # AI_AGENT_001
│   ├── security_rules.py # AI_SECRET_001
│   └── prompt_rules.py  # AI_PROMPT_001
├── scanner.py           # Walks .py files, applies rules, collects findings
├── reporter.py          # Terminal (ANSI color) and JSON formatters
└── __main__.py          # CLI entry point
```

Each rule is an independent class with a `check(tree, filepath) -> list[Finding]` interface. The scanner applies all rules to each file's AST. Adding a new rule means adding one class — no changes to the scanner or CLI.

**Zero runtime dependencies.** Uses only Python stdlib: `ast`, `argparse`, `json`, `dataclasses`, `pathlib`.

---

## How detection works

Rules use Python's built-in `ast` module to parse source files into an Abstract Syntax Tree and then pattern-match against it.

For example, `AI_LLM_001` walks the AST looking for:
- LangChain-style constructor calls (`ChatOpenAI(...)`, `ChatAnthropic(...)`) missing `model=`
- Raw SDK calls (`.messages.create(messages=[...])`) missing `model=`

The `messages=` kwarg requirement in the second check prevents false positives on unrelated `.create()` calls like `db.records.create(name="test")`.

`AI_AGENT_001` uses a custom `_walk_no_nested_fns()` traversal that stops at nested function/class boundaries — so a `while True:` inside a nested callback is attributed to that inner function, not its parent.

### Which files get scanned

Scanning a directory recursively globs for `*.py` and parses every match — there's no content sniffing to decide "is this file AI-related" ahead of time; each rule's own AST pattern is the filter (a file with no LLM-call-shaped code simply produces no findings). What *is* excluded by name: any path under a `.`-prefixed directory (`.venv`, `.git`, ...) or a known non-source directory (`__pycache__`, `venv`, `env`, `build`, `dist`, `node_modules`, `site-packages`). Without that exclusion, `scan .` from a project root would also parse every vendored dependency in your virtualenv — scanning this repo's own `.venv` turns up 747 `.py` files, almost all of them pip/setuptools internals. Scanning a single file with `scan path/to/file.py` always runs on exactly that file, with no exclusion logic applied.

---

## Setup

Requires Python 3.11+.

```bash
pip install -e ".[dev]"      # installs pytest + the ai-quality-analyzer CLI
python -m pytest -v          # run the test suite
```

---

## Demo

See [`DEMO.md`](DEMO.md) for a live walkthrough script (talking points + commands, interview-ready). The GIF at the top of this README is generated from [`demo.tape`](demo.tape) — regenerate it after any output-affecting change with:

```bash
brew install vhs            # one-time; scripted terminal recorder
vhs demo.tape                # writes demo.gif
```

---

## Background

This project is a portfolio demonstration of applying rule-based static analysis — a discipline common in safety-critical engineering (MISRA, MXAM, Model Advisor) — to the emerging domain of LLM application quality. The same pattern of named rules with severity levels, rationale, and findable locations maps directly to how production AI governance tooling works.
