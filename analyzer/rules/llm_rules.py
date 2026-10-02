import ast
from .base import Finding, Rule, Severity, _walk_no_nested_fns

LLM_CONSTRUCTORS: set[str] = {
    "ChatOpenAI", "AzureChatOpenAI", "ChatAnthropic", "ChatBedrock",
    "ChatOllama", "ChatGoogleGenerativeAI", "ChatMistralAI",
    "ChatGroq", "ChatCohere", "LlamaCpp",
}

LLM_API_METHODS: set[str] = {"create", "invoke", "generate", "run", "complete"}


def _get_kwarg_names(call: ast.Call) -> set[str]:
    return {kw.arg for kw in call.keywords if kw.arg is not None}


def _is_llm_constructor_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id in LLM_CONSTRUCTORS


def _is_llm_api_call(call: ast.Call) -> bool:
    """True if this looks like a raw LLM API call: a method in LLM_API_METHODS
    that also has a messages= or prompt= kwarg (distinguishes it from e.g. db.create())."""
    if not isinstance(call.func, ast.Attribute):
        return False
    if call.func.attr not in LLM_API_METHODS:
        return False
    return bool(_get_kwarg_names(call) & {"messages", "prompt", "inputs", "input"})


def _is_llm_call(call: ast.Call) -> bool:
    return _is_llm_constructor_call(call) or _is_llm_api_call(call)


class ModelNotConfiguredRule(Rule):
    rule_id = "AI_LLM_001"
    title = "LLM model identifier not explicitly configured"
    rationale = (
        "Relying on a provider default model causes silent behavior changes "
        "when provider defaults are updated. Always pin the model name."
    )
    severity = Severity.ERROR

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_llm_call(node):
                continue
            if "model" not in _get_kwarg_names(node):
                findings.append(self._finding(
                    "LLM call is missing required 'model=' argument.",
                    filepath,
                    getattr(node, "lineno", None),
                ))
        return findings


class TemperatureNotConfiguredRule(Rule):
    rule_id = "AI_LLM_002"
    title = "LLM temperature not explicitly configured"
    rationale = (
        "Provider defaults for temperature vary and change over time. "
        "Explicit configuration ensures reproducible, predictable outputs."
    )
    severity = Severity.WARNING

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_llm_call(node):
                continue
            if "temperature" not in _get_kwarg_names(node):
                findings.append(self._finding(
                    "LLM call is missing 'temperature=' argument.",
                    filepath,
                    getattr(node, "lineno", None),
                ))
        return findings


class NoErrorHandlingRule(Rule):
    rule_id = "AI_LLM_003"
    title = "No error handling around LLM calls"
    rationale = (
        "LLM APIs fail more often and in more varied ways than typical REST calls — "
        "rate limits, timeouts, content filtering — and an uncaught exception from a "
        "single LLM call takes down the entire request path around it. Wrap the call "
        "in a try/except for the provider's error types."
    )
    severity = Severity.WARNING

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            llm_calls = [
                n for n in _walk_no_nested_fns(node)
                if isinstance(n, ast.Call) and _is_llm_api_call(n)
            ]
            if not llm_calls:
                continue
            has_try = any(isinstance(n, ast.Try) for n in _walk_no_nested_fns(node))
            if not has_try:
                findings.append(self._finding(
                    f"Function '{node.name}' makes an LLM call with no try/except in scope.",
                    filepath,
                    llm_calls[0].lineno,
                ))
        return findings
