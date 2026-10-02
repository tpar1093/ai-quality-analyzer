import json
from pathlib import Path
import pytest
from analyzer.scanner import scan_file, scan_directory, ALL_RULES

BAD_CODE = """\
from anthropic import Anthropic
client = Anthropic()

def answer(question, docs):
    context = "\\n".join(docs)
    response = client.messages.create(
        messages=[{"role": "user", "content": context}],
        max_tokens=256,
    )
    return response.content[0].text

def retrieve(query):
    raw = [{"content": "Paris", "source": "wiki.txt"}]
    return [doc["content"] for doc in raw]

def run_agent(question):
    while True:
        docs = retrieve(question)
        result = answer(question, docs)
        if result:
            return result
"""

CLEAN_CODE = """\
x = 1 + 1
"""


def test_scan_file_returns_findings_for_bad_code(tmp_path: Path):
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    findings = scan_file(target)
    assert len(findings) > 0


def test_scan_file_finds_expected_rule_ids(tmp_path: Path):
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    findings = scan_file(target)
    rule_ids = {f.rule_id for f in findings}
    assert "AI_LLM_001" in rule_ids
    assert "AI_LLM_002" in rule_ids
    assert "AI_OUTPUT_001" in rule_ids
    assert "AI_RAG_001" in rule_ids
    assert "AI_RAG_002" in rule_ids
    assert "AI_AGENT_001" in rule_ids


def test_scan_file_returns_empty_for_clean_code(tmp_path: Path):
    target = tmp_path / "clean.py"
    target.write_text(CLEAN_CODE)
    findings = scan_file(target)
    assert findings == []


def test_scan_file_silently_skips_syntax_errors(tmp_path: Path):
    target = tmp_path / "broken.py"
    target.write_text("def (:")
    findings = scan_file(target)
    assert findings == []


def test_scan_directory_recurses_into_subdirs(tmp_path: Path):
    subdir = tmp_path / "app"
    subdir.mkdir()
    (subdir / "main.py").write_text(BAD_CODE)
    (subdir / "helpers.py").write_text(CLEAN_CODE)
    findings = scan_directory(tmp_path)
    assert any("main.py" in f.file for f in findings)
    assert not any("helpers.py" in f.file for f in findings)


def test_scan_directory_skips_non_python_files(tmp_path: Path):
    (tmp_path / "README.md").write_text("# readme")
    (tmp_path / "app.py").write_text(CLEAN_CODE)
    findings = scan_directory(tmp_path)
    assert findings == []


def test_scan_directory_skips_venv_directory(tmp_path: Path):
    venv_pkg = tmp_path / ".venv" / "lib" / "site-packages"
    venv_pkg.mkdir(parents=True)
    (venv_pkg / "dep.py").write_text(BAD_CODE)
    (tmp_path / "app.py").write_text(CLEAN_CODE)
    findings = scan_directory(tmp_path)
    assert findings == []


def test_scan_directory_skips_pycache_directory(tmp_path: Path):
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "app.cpython-311.py").write_text(BAD_CODE)
    findings = scan_directory(tmp_path)
    assert findings == []


def test_scan_directory_skips_git_directory(tmp_path: Path):
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    (git_dir / "pre-commit.py").write_text(BAD_CODE)
    findings = scan_directory(tmp_path)
    assert findings == []


def test_scan_directory_still_scans_normal_subdirs(tmp_path: Path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text(BAD_CODE)
    findings = scan_directory(tmp_path)
    assert len(findings) > 0


def test_all_rules_list_has_ten_entries():
    assert len(ALL_RULES) == 10
    rule_ids = [r.rule_id for r in ALL_RULES]
    assert "AI_LLM_001" in rule_ids
    assert "AI_LLM_002" in rule_ids
    assert "AI_LLM_003" in rule_ids
    assert "AI_OUTPUT_001" in rule_ids
    assert "AI_RAG_001" in rule_ids
    assert "AI_RAG_002" in rule_ids
    assert "AI_RAG_003" in rule_ids
    assert "AI_AGENT_001" in rule_ids
    assert "AI_SECRET_001" in rule_ids
    assert "AI_PROMPT_001" in rule_ids


# --- Integration tests against examples/ (skip if not yet created) ---

def test_bad_app_triggers_all_ten_rules():
    bad_app = Path(__file__).parent.parent / "examples" / "bad_app"
    if not bad_app.exists():
        pytest.skip("examples/bad_app not yet created")
    findings = scan_directory(bad_app)
    rule_ids = {f.rule_id for f in findings}
    assert rule_ids == {
        "AI_LLM_001", "AI_LLM_002", "AI_LLM_003", "AI_OUTPUT_001",
        "AI_RAG_001", "AI_RAG_002", "AI_RAG_003", "AI_AGENT_001",
        "AI_SECRET_001", "AI_PROMPT_001",
    }


def test_good_app_has_zero_findings():
    good_app = Path(__file__).parent.parent / "examples" / "good_app"
    if not good_app.exists():
        pytest.skip("examples/good_app not yet created")
    findings = scan_directory(good_app)
    assert findings == [], f"Unexpected findings: {findings}"


def test_cli_scan_exits_1_with_findings(tmp_path):
    import subprocess, sys
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", str(target)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 1
    assert "AI_LLM_001" in result.stdout


def test_cli_scan_json_format(tmp_path):
    import subprocess, sys
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", str(target), "--format", "json"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert any(d["rule_id"] == "AI_LLM_001" for d in data)


def test_cli_scan_exits_0_for_clean_file(tmp_path):
    import subprocess, sys
    target = tmp_path / "clean.py"
    target.write_text(CLEAN_CODE)
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", str(target)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0


def test_cli_error_on_nonexistent_path():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", "/no/such/path"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode != 0


def test_cli_rule_filter_runs_only_that_rule(tmp_path):
    import subprocess, sys
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", str(target), "--rule", "AI_LLM_001", "--format", "json"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    data = json.loads(result.stdout)
    rule_ids = {d["rule_id"] for d in data}
    assert rule_ids == {"AI_LLM_001"}


def test_cli_rule_filter_accepts_multiple_rules(tmp_path):
    import subprocess, sys
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", str(target),
         "--rule", "AI_LLM_001", "--rule", "AI_RAG_001", "--format", "json"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    data = json.loads(result.stdout)
    rule_ids = {d["rule_id"] for d in data}
    assert rule_ids == {"AI_LLM_001", "AI_RAG_001"}


def test_cli_rule_filter_errors_on_unknown_rule_id(tmp_path):
    import subprocess, sys
    target = tmp_path / "bad.py"
    target.write_text(BAD_CODE)
    result = subprocess.run(
        [sys.executable, "-m", "analyzer", "scan", str(target), "--rule", "AI_NOT_REAL"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 2
    assert "AI_NOT_REAL" in result.stderr
