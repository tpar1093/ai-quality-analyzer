import ast
import pytest
from analyzer.rules.agent_rules import UnboundedAgentLoopRule


def parse(code: str) -> ast.AST:
    return ast.parse(code)


class TestUnboundedAgentLoopRule:
    rule = UnboundedAgentLoopRule()

    def test_flags_while_true_in_function(self):
        code = """
def run_agent(question):
    while True:
        result = call_llm(question)
        if "done" in result:
            return result
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_AGENT_001"
        assert findings[0].severity == "error"

    def test_no_finding_for_bounded_range_loop(self):
        code = """
MAX_STEPS = 10

def run_agent(question):
    for step in range(MAX_STEPS):
        result = call_llm(question)
        if result:
            return result
    return "max steps reached"
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_while_true_in_nested_function_flagged_on_inner_not_outer(self):
        code = """
def outer():
    def inner():
        while True:
            pass
    return inner
"""
        findings = self.rule.check(parse(code), "test.py")
        # inner() should be flagged, outer() should not
        names = [f.message for f in findings]
        assert any("inner" in msg for msg in names)
        assert not any("outer" in msg for msg in names)

    def test_flags_async_function_with_while_true(self):
        code = """
async def run_agent(question):
    while True:
        result = await call_llm(question)
        if result:
            return result
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_AGENT_001"

    def test_finding_includes_while_line_number(self):
        code = """\
def run_agent(q):
    x = 1
    while True:
        pass
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings[0].line == 3

    def test_no_finding_for_module_level_while_true(self):
        code = """
while True:
    handle_request()
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_no_finding_for_repl_loop_gated_by_input(self):
        code = """
def run_agent():
    while True:
        user_input = input("You: ").strip()
        if user_input == "quit":
            break
        result = call_llm(user_input)
        print(result)
"""
        findings = self.rule.check(parse(code), "test.py")
        assert findings == []

    def test_flags_inner_llm_loop_even_when_outer_repl_loop_is_exempt(self):
        code = """\
def run_agent():
    while True:
        user_input = input("You: ").strip()
        if user_input == "quit":
            break
        while True:
            response = call_llm(user_input)
            if not response.tool_calls:
                break
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 1
        assert findings[0].rule_id == "AI_AGENT_001"
        assert findings[0].line == 6

    def test_flags_both_unbounded_loops_in_same_function(self):
        code = """
def run_agent():
    while True:
        call_llm("a")
    while True:
        call_llm("b")
"""
        findings = self.rule.check(parse(code), "test.py")
        assert len(findings) == 2
