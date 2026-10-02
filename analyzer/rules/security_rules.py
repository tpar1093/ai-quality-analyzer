import ast
from .base import Finding, Rule, Severity

CREDENTIAL_KWARGS: set[str] = {
    "api_key", "auth_token", "access_token", "secret", "secret_key", "password",
}


class HardcodedCredentialRule(Rule):
    rule_id = "AI_SECRET_001"
    title = "Credential passed as a hardcoded string literal"
    rationale = (
        "A literal string value is written into the source file and therefore into "
        "git history permanently — removing it in a later commit does not purge it "
        "from history, and rotating the credential does not revoke access for anyone "
        "who already cloned or mirrored the repository. Load credentials at runtime "
        "via an environment variable or a secret manager, never as a literal in code."
    )
    severity = Severity.ERROR

    def check(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg not in CREDENTIAL_KWARGS:
                    continue
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) and kw.value.value != "":
                    findings.append(self._finding(
                        f"'{kw.arg}=' is passed a hardcoded string literal.",
                        filepath,
                        getattr(node, "lineno", None),
                    ))
        return findings
