import ast
from .base import Finding, Rule, Severity
from .llm_rules import _is_llm_api_call


def _is_single_field_access(elt: ast.expr, var_name: str) -> bool:
    """True if elt is exactly one field/key access on var_name.
    Matches doc["content"] (Subscript) and doc.page_content (Attribute).
    Does NOT match: doc, {"content": doc["content"], ...}, f"[{doc.source}] ..."
    """
    if isinstance(elt, ast.Subscript) and isinstance(elt.value, ast.Name):
        return elt.value.id == var_name
    if isinstance(elt, ast.Attribute) and isinstance(elt.value, ast.Name):
        return elt.value.id == var_name
    return False


def _is_raw_llm_string(node: ast.expr) -> bool:
    """True if node matches common raw LLM response string access patterns:
    - Anthropic: response.content[N].text
    - OpenAI:    response.choices[N].message.content
    """
    if not isinstance(node, ast.Attribute):
        return False

    if node.attr == "text":
        current: ast.expr = node.value
        while isinstance(current, (ast.Attribute, ast.Subscript)):
            if isinstance(current, ast.Attribute) and current.attr == "content":
                return True
            current = current.value  # type: ignore[attr-defined]
        return False

    if node.attr == "content":
        current = node.value
        while isinstance(current, (ast.Attribute, ast.Subscript)):
            if isinstance(current, ast.Attribute) and current.attr in {"message", "choices"}:
                return True
            current = current.value  # type: ignore[attr-defined]
        return False

    return False


class MetadataStrippedRule(Rule):
    rule_id = "AI_RAG_001"
    title = "Retrieved documents strip source metadata"
    rationale = (
        "Dropping metadata (source, chunk_id, score) from retrieved documents "
        "prevents downstream attribution, filtering, and debugging."
    )
    severity = Severity.ERROR

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ListComp) or not node.generators:
                continue
            gen = node.generators[0]
            if not isinstance(gen.target, ast.Name):
                continue
            var_name = gen.target.id
            if _is_single_field_access(node.elt, var_name):
                iter_name = gen.iter.id if isinstance(gen.iter, ast.Name) else "docs"
                findings.append(self._finding(
                    f"List comprehension over '{iter_name}' discards document metadata.",
                    filepath,
                    getattr(node, "lineno", None),
                ))
        return findings


class SourceAttributionMissingRule(Rule):
    rule_id = "AI_RAG_002"
    title = "Generated answer missing source attribution"
    rationale = (
        "RAG answers must reference their source documents so users can verify "
        "claims and so the system can be audited."
    )
    severity = Severity.WARNING

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            has_llm_call = any(
                _is_llm_api_call(n)
                for n in ast.walk(node)
                if isinstance(n, ast.Call)
            )
            if not has_llm_call:
                continue

            for ret in ast.walk(node):
                if isinstance(ret, ast.Return) and ret.value is not None:
                    if _is_raw_llm_string(ret.value):
                        findings.append(self._finding(
                            f"Function '{node.name}' returns raw LLM text without source attribution.",
                            filepath,
                            ret.lineno,
                        ))
                        break
        return findings
