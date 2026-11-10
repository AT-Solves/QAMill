"""
Regression tests for the mutation and test-generation repairs.

Run from the backend directory:  python -m pytest test_mutation_regressions.py -q
"""
import asyncio
import json
from pathlib import Path

import pytest

from javascript_mutation_engine import JavaScriptMutationEngine
from javascript_test_runner import JestTestRunner
import test_generator as tg


JS_SOURCE = """\
/**
 * Calculator - comment with a - sign and a * star
 */
function add(a, b) { return a + b; }
function same(a, b) { return a === b; }
function different(a, b) { return a !== b; }
function bigger(a, b) { return a > b; }
"""


@pytest.fixture
def js_file(tmp_path: Path) -> Path:
    path = tmp_path / "calc.js"
    path.write_text(JS_SOURCE, encoding="utf-8")
    return path


def _mutants(js_file: Path):
    engine = JavaScriptMutationEngine(str(js_file.parent))
    return engine.generate_mutants(str(js_file))


def test_js_mutants_carry_full_source(js_file):
    """A mutant must be the whole mutated module, never a bare fragment."""
    original = JS_SOURCE
    mutants = _mutants(js_file)
    assert mutants, "expected mutants for the sample source"
    for m in mutants:
        assert len(m.mutant_src) > len(original) // 2, f"{m.id} is a fragment"
        assert m.mutant_src != original, f"{m.id} is a no-op"


def test_js_arithmetic_operator_is_matched(js_file):
    descriptions = {m.description for m in _mutants(js_file) if m.operator == "AOR"}
    assert "+ → -" in descriptions


def test_js_relational_operator_not_matched_inside_longer_operator(js_file):
    """'==' must not match inside '===' or '!==' (would give invalid '!!=')."""
    for m in _mutants(js_file):
        assert "!!=" not in m.mutant_src
    ror = [m for m in _mutants(js_file) if m.operator == "ROR"]
    assert ror, "expected relational mutants"


def test_js_comment_lines_produce_no_mutants(js_file):
    """Mutating comment text is meaningless and must not enter the score."""
    comment_lines = {1, 2, 3}
    assert all(m.line_no not in comment_lines for m in _mutants(js_file))


def test_jest_runner_error_is_not_classified_as_survived(js_file, monkeypatch):
    """A runner failure must surface as an execution error, not a surviving mutant."""
    runner = JestTestRunner(str(js_file.parent))
    monkeypatch.setattr(
        runner, "run_tests",
        lambda test_files=None, coverage=False: {
            "status": "error", "passed": 0, "failed": 0, "total": 0,
            "error": "Jest tests timed out (60s limit)",
        },
    )
    mutant = _mutants(js_file)[0]
    result = asyncio.run(runner.test_mutant(mutant, []))
    assert result["status"] == "error"


def test_jest_runner_restores_source_after_mutant(js_file, monkeypatch):
    runner = JestTestRunner(str(js_file.parent))
    monkeypatch.setattr(
        runner, "run_tests",
        lambda test_files=None, coverage=False: {
            "status": "success", "passed": 1, "failed": 0, "total": 1, "error": None,
        },
    )
    mutant = _mutants(js_file)[0]
    asyncio.run(runner.test_mutant(mutant, []))
    assert js_file.read_text(encoding="utf-8") == JS_SOURCE


def test_extract_cases_never_invents_cases_for_garbage():
    assert tg.TestGenerator._extract_json_cases("no json here at all") == []


def test_extract_cases_recovers_complete_objects_from_truncated_output():
    cases = [
        {"id": f"TC-{i:03d}", "title": f"Case {i}", "priority": "High",
         "preconditions": "Loaded", "steps": ["Call add(2, 3)"], "expected": "5"}
        for i in range(1, 6)
    ]
    full = json.dumps(cases, indent=2)
    truncated = "```json\n" + full[: int(len(full) * 0.7)]
    recovered = tg.TestGenerator._extract_json_cases(truncated)
    assert 0 < len(recovered) < len(cases)
    assert all(c["title"].startswith("Case ") for c in recovered), "only real model cases"


def test_extract_cases_valid_json_round_trips():
    cases = [{"id": "TC-001", "title": "t", "priority": "Low",
              "preconditions": "", "steps": [], "expected": "x"}]
    assert tg.TestGenerator._extract_json_cases(json.dumps(cases)) == cases


# ── Isolation: the JS job must never modify the original project ─────────────

def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_js_job_never_modifies_original_source(tmp_path, monkeypatch):
    """Run the real JS job on a temp project; original checksum and workspace must survive."""
    import tempfile
    import main

    sample = Path(__file__).resolve().parent.parent / "sample_project"
    project = tmp_path / "proj"
    project.mkdir()
    for name in ("calculator.js", "calculator.test.js", "jest.config.js"):
        (project / name).write_bytes((sample / name).read_bytes())
    source = project / "calculator.js"
    before = _sha256(source)

    tmp_root = Path(tempfile.gettempdir())
    before_jobs = set(tmp_root.glob("qamill_job_*"))

    job_id = "test-isolation-job"
    main._job_events[job_id] = []
    main._job_subs[job_id] = []
    req = main.AnalyzeRequest(file_path=str(source), project_root=str(project), llm_provider="none")
    asyncio.run(main._run_javascript_analysis(job_id, req, "jest"))

    events = main._job_events[job_id]
    assert any(e.get("type") == "complete" for e in events), events[-1:]
    assert _sha256(source) == before, "original source was modified"
    leftover = set(tmp_root.glob("qamill_job_*")) - before_jobs
    assert not leftover, f"workspace not cleaned up: {leftover}"


# ── Gap-driven test generation ──────────────────────────────────────────────

class _StubLLM:
    """Stands in for a provider. Returns a fixed reply and records the prompts."""
    name = "stub"

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts = []

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        self.prompts.append(prompt)
        return self.reply


def _gap_project(tmp_path):
    project = tmp_path / "proj"
    (project / "qamill-reports").mkdir(parents=True)
    (project / "test_calc.py").write_text(
        "def test_add_basic():\n    assert add(1, 2) == 3\n", encoding="utf-8")
    source = project / "calc.py"
    source.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    import mutation_gaps
    gaps = [{
        "mutant_id": "M0001", "operator": "AOR", "function": "add", "line": 2,
        "change": "+ -> -", "original_code": "return a + b", "mutated_code": "return a - b",
        "priority": "high", "why_survived": "x", "missing_assertion": "y", "expected_behaviour": "z",
    }]
    mutation_gaps.write_gap_file(str(project), str(source), "job", 2, 1, gaps)
    return project, source


def test_gap_generation_refuses_without_gap_file(tmp_path):
    import test_generator as tg
    project = tmp_path / "empty"
    project.mkdir()
    source = project / "calc.py"
    source.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    stub = _StubLLM("```json\n[]\n```")
    gen = tg.TestGenerator(stub, str(project))
    result = asyncio.run(gen.generate_manual_tests(str(source), gap_driven=True))
    assert result["success"] is False and "Run mutation analysis first" in result["message"]
    assert stub.prompts == [], "no LLM call without gap records"


def test_gap_generation_links_dedups_and_drops_unlinked(tmp_path):
    import test_generator as tg
    project, source = _gap_project(tmp_path)
    reply = """```json
[
  {"title": "Add returns difference", "objective": "o", "priority": "High",
   "preconditions": "p", "steps": ["add(5,2)"], "expected": "3",
   "coverage_gap": "AOR", "mutation_ids": ["M0001"]},
  {"title": "Add basic", "priority": "High", "steps": [], "expected": "3",
   "mutation_ids": ["M0001"]},
  {"title": "Unlinked case", "steps": [], "expected": "x", "mutation_ids": ["M9999"]},
  {"title": "Add returns difference", "steps": [], "expected": "3", "mutation_ids": ["M0001"]}
]
```"""
    gen = tg.TestGenerator(_StubLLM(reply), str(project))
    result = asyncio.run(gen.generate_manual_tests(str(source), gap_driven=True))
    assert result["success"] is True
    titles = [c["title"] for c in result["cases"]]
    assert titles == ["Add returns difference"]          # existing "Add basic" removed, unlinked removed
    assert result["cases"][0]["mutation_ids"] == ["M0001"]
    assert result["duplicates_removed"] == 2 and result["unlinked_removed"] == 1
    assert "M0001" in result["content"]


def test_gap_generation_reports_failure_instead_of_inventing(tmp_path):
    import test_generator as tg
    project, source = _gap_project(tmp_path)
    gen = tg.TestGenerator(_StubLLM("```json\n[{\"title\": \"no link\", \"mutation_ids\": []}]\n```"),
                           str(project))
    result = asyncio.run(gen.generate_manual_tests(str(source), gap_driven=True))
    assert result["success"] is False
    assert result["cases"] == []


def test_gemini_without_key_fails_explicitly_and_never_logs_key(monkeypatch, capsys):
    from llm_adapter import GeminiAdapter
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    adapter = GeminiAdapter(api_key=None)
    with pytest.raises(ValueError, match="Gemini API key is not configured"):
        asyncio.run(adapter.call_async("hello"))


def test_gemini_key_is_not_written_to_logs(monkeypatch, capsys):
    from llm_adapter import GeminiAdapter
    secret = "SECRET-TEST-KEY-123456"
    GeminiAdapter(api_key=secret)
    captured = capsys.readouterr()
    assert secret not in captured.out and secret not in captured.err


def test_fallback_is_reported_explicitly(tmp_path):
    """When the chosen provider fails and fallback is allowed, the result says so."""
    import test_generator as tg

    class _Failing(_StubLLM):
        name = "gemini"

        async def call_async(self, prompt, max_tokens=500):
            raise RuntimeError("quota exceeded")

    class _Local(_StubLLM):
        name = "ollama"

    project, source = _gap_project(tmp_path)
    reply = '```json\n[{"title": "Add subtracts", "steps": ["add(5,2)"], "expected": "3", "mutation_ids": ["M0001"]}]\n```'
    gen = tg.TestGenerator(_Failing("x"), str(project), fallback_llm=_Local(reply))
    result = asyncio.run(gen.generate_manual_tests(str(source), gap_driven=True))
    assert result["success"] is True
    assert result["provider_used"] == "ollama (fallback)"
    assert "gemini failed" in result["fallback_reason"]
