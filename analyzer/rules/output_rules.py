import ast
from .base import Finding, Rule, Severity
from .llm_rules import _is_llm_api_call, _get_kwarg_names


class UnstructuredOutputRule(Rule):
    rule_id = "AI_OUTPUT_001"
    title = "Machine-consumed LLM output lacks structured schema"
    rationale = (
        "LLM output consumed by code should be validated against a schema "
        "(json.loads, Pydantic, or response_format). Raw strings break silently "
        "when the model changes its output format."
    )
    severity = Severity.WARNING

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            llm_calls = [
                n for n in ast.walk(node)
                if isinstance(n, ast.Call) and _is_llm_api_call(n)
            ]
            if not llm_calls:
                continue

            has_json_loads = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "loads"
                for n in ast.walk(node)
            )
            has_response_format = any(
                "response_format" in _get_kwarg_names(call) for call in llm_calls
            )
            has_structured_output = any(
                isinstance(n, ast.Attribute) and n.attr == "with_structured_output"
                for n in ast.walk(node)
            )

            if not (has_json_loads or has_response_format or has_structured_output):
                findings.append(self._finding(
                    f"Function '{node.name}' makes LLM calls without structured output parsing.",
                    filepath,
                    node.lineno,
                ))
        return findings
