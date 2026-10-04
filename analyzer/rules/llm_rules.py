import ast
from .base import Finding, Rule, Severity, _walk_no_nested_fns

LLM_CONSTRUCTORS: set[str] = {
    "ChatOpenAI", "AzureChatOpenAI", "ChatAnthropic", "ChatBedrock",
    "ChatOllama", "ChatGoogleGenerativeAI", "ChatMistralAI",
    "ChatGroq", "ChatCohere", "LlamaCpp",
    # init_chat_model is LangChain's current provider-agnostic initializer —
    # the documented, recommended replacement for constructing a Chat*
    # class directly in newer LangChain code.
    "init_chat_model",
}

LLM_API_METHODS: set[str] = {"create", "invoke", "generate", "run", "complete", "chat"}

# Bare top-level functions that are themselves a specific, known LLM SDK's
# public API — not a guess at a user's wrapper-function name. LiteLLM's
# `completion`/`acompletion` are the main examples of a widely-used LLM
# client whose call shape is a bare function rather than a method.
LLM_BARE_FUNCTIONS: set[str] = {"completion", "acompletion"}

LLM_CALL_KWARGS: set[str] = {"messages", "prompt", "inputs", "input"}


def _get_kwarg_names(call: ast.Call) -> set[str]:
    return {kw.arg for kw in call.keywords if kw.arg is not None}


def _is_llm_constructor_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id in LLM_CONSTRUCTORS


def _is_llm_api_call(call: ast.Call) -> bool:
    """True if this looks like a raw LLM API call: either a method in
    LLM_API_METHODS (e.g. client.messages.create(...)) or a bare call to a
    known LLM library function (e.g. litellm's completion(...)) — in both
    cases only when it also has a messages=/prompt= kwarg (distinguishes it
    from e.g. db.create() or an unrelated completion(tasks) call)."""
    if isinstance(call.func, ast.Attribute):
        name_matches = call.func.attr in LLM_API_METHODS
    elif isinstance(call.func, ast.Name):
        name_matches = call.func.id in LLM_BARE_FUNCTIONS
    else:
        return False
    if not name_matches:
        return False
    return bool(_get_kwarg_names(call) & LLM_CALL_KWARGS)


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


class NoMaxTokensLimitRule(Rule):
    rule_id = "AI_LLM_004"
    title = "LLM call has no max_tokens limit"
    rationale = (
        "Without an explicit max_tokens (or max_completion_tokens) cap, a single "
        "call's cost and latency are unbounded — a model producing an unexpectedly "
        "long response can consume far more budget than intended with no ceiling. "
        "Pin an explicit limit sized to the expected response."
    )
    severity = Severity.WARNING

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_llm_call(node):
                continue
            if not (_get_kwarg_names(node) & {"max_tokens", "max_completion_tokens"}):
                findings.append(self._finding(
                    "LLM call is missing a 'max_tokens='/'max_completion_tokens=' limit.",
                    filepath,
                    getattr(node, "lineno", None),
                ))
        return findings
