import ast
from .base import Finding, Rule, Severity


def _literal_text(value: ast.expr) -> str | None:
    """Return the literal text of a string Constant or f-string (JoinedStr),
    or None if value isn't a literal string expression."""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.JoinedStr):
        return "".join(p.value for p in value.values if isinstance(p, ast.Constant))
    return None


def _dict_str_value(node: ast.Dict, key_name: str) -> ast.expr | None:
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and key.value == key_name:
            return value
    return None


class HardcodedSystemPromptRule(Rule):
    rule_id = "AI_PROMPT_001"
    title = "System prompt is hardcoded inline rather than externalized"
    rationale = (
        "System prompts are edited far more often than application logic — by prompt "
        "engineers, during A/B tests, or in response to model behavior changes — and a "
        "prompt embedded directly in a function call has no version history independent "
        "of the surrounding code, cannot be diffed or rolled back on its own, and forces "
        "a full code review and deploy for a wording change. Externalize it to a "
        "dedicated file or a prompts module loaded at runtime."
    )
    severity = Severity.WARNING
    MIN_LENGTH = 120

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg != "system":
                        continue
                    text = _literal_text(kw.value)
                    if text is not None and len(text) >= self.MIN_LENGTH:
                        findings.append(self._finding(
                            f"'system=' is a hardcoded literal {len(text)} characters long.",
                            filepath,
                            getattr(node, "lineno", None),
                        ))
            elif isinstance(node, ast.Dict):
                role = _dict_str_value(node, "role")
                if not (isinstance(role, ast.Constant) and role.value == "system"):
                    continue
                content = _dict_str_value(node, "content")
                if content is None:
                    continue
                text = _literal_text(content)
                if text is not None and len(text) >= self.MIN_LENGTH:
                    findings.append(self._finding(
                        f"System message 'content' is a hardcoded literal {len(text)} characters long.",
                        filepath,
                        getattr(node, "lineno", None),
                    ))
        return findings
