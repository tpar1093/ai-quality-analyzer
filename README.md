# ai-quality-analyzer

Static analysis for LLM and RAG applications — rule-based quality checking inspired by automotive tools like MXAM and Model Advisor.

Scans Python source files using AST analysis and reports violations as structured findings with rule ID, severity, rationale, and location.

---

## Rules

| Rule ID | Title | Severity |
|---|---|---|
| `AI_LLM_001` | LLM model identifier not explicitly configured | ERROR |
| `AI_LLM_002` | LLM temperature not explicitly configured | WARNING |
| `AI_OUTPUT_001` | Machine-consumed LLM output lacks structured schema | WARNING |
| `AI_RAG_001` | Retrieved documents strip source metadata | ERROR |
| `AI_RAG_002` | Generated answer missing source attribution | WARNING |
| `AI_AGENT_001` | Agent workflow has no maximum step limit | ERROR |

---

## Usage

```bash
# Scan a directory — terminal output
python -m analyzer scan ./my_app

# Scan a single file
python -m analyzer scan ./my_app/rag.py

# JSON output (for CI or tooling integration)
python -m analyzer scan ./my_app --format json
```

Exit code `0` = no findings. Exit code `1` = findings found. Suitable for use in CI pipelines.

---

## Example

Running against the included bad example app:

```
python -m analyzer scan ./examples/bad_app
```

```
[ERROR] AI_LLM_001: LLM model identifier not explicitly configured
  Location : examples/bad_app/rag_app.py:31
  Finding  : LLM call is missing required 'model=' argument.
  Rationale: Relying on a provider default model causes silent behavior changes
             when provider defaults are updated. Always pin the model name.

[WARNING] AI_LLM_002: LLM temperature not explicitly configured
  ...

[ERROR] AI_RAG_001: Retrieved documents strip source metadata
  Location : examples/bad_app/rag_app.py:24
  Finding  : List comprehension over 'raw_docs' discards document metadata.
  ...

Total: 6 finding(s)
```

The `examples/good_app/` version of the same application passes all checks.

---

## Architecture

```
analyzer/
├── rules/
│   ├── base.py          # Finding dataclass, Rule ABC, AST walk helper
│   ├── llm_rules.py     # AI_LLM_001, AI_LLM_002
│   ├── output_rules.py  # AI_OUTPUT_001
│   ├── rag_rules.py     # AI_RAG_001, AI_RAG_002
│   └── agent_rules.py   # AI_AGENT_001
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

---

## Setup

Requires Python 3.11+.

```bash
pip install pytest          # only dev dependency
python -m pytest -v         # run the 56-test suite
```

---

## Background

This project is a portfolio demonstration of applying rule-based static analysis — a discipline common in safety-critical engineering (MISRA, MXAM, Model Advisor) — to the emerging domain of LLM application quality. The same pattern of named rules with severity levels, rationale, and findable locations maps directly to how production AI governance tooling works.
