"""
Regression tests: Gemini HTTP 429 handling, missing credentials, and provider switching.

Run from the backend directory:  python -m pytest test_llm_failures.py -q
"""
import asyncio
import json
from pathlib import Path

import pytest

import llm_adapter
import test_generator as tg
from llm_adapter import GeminiAdapter, LLMProviderError, classify_gemini_429

FAKE_KEY = "TEST-KEY-DO-NOT-USE-0123456789"
QUOTA_BODY = json.dumps({"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": "You exceeded your current quota, please check your plan and billing details."}})
RATE_BODY = json.dumps({"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": "Rate limit exceeded: requests per minute.",
    "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "30s"}]}})

QUOTA_MSG = ("Gemini quota exhausted. Check your Google AI Studio usage and billing, "
             "or choose another configured provider.")
RATE_MSG = "Gemini rate limit reached. Please wait before retrying."
MISSING_MSG = "Gemini API key is not configured."


# ── HTTP 429 classification ──────────────────────────────────────────────────

def test_quota_exhaustion_is_classified_as_quota():
    assert classify_gemini_429(QUOTA_BODY, {}) == "quota_exhausted"


def test_retry_hint_means_temporary_rate_limit():
    assert classify_gemini_429(RATE_BODY, {}) == "rate_limited"


def test_live_quota_response_with_retry_info_is_quota_not_rate_limit():
    """Shape of a real Gemini billing-quota 429: RetryInfo is present but the error is quota."""
    live = json.dumps({"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
        "message": "You exceeded your current quota, please check your plan and billing details.",
        "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure"},
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "35s"}]}})
    assert classify_gemini_429(live, {}) == "quota_exhausted"


def test_quota_wording_wins_even_when_quota_detail_names_a_per_minute_metric():
    """A billing-quota 429 whose QuotaFailure detail id contains 'PerMinute' is still quota."""
    body = json.dumps({"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
        "message": "You exceeded your current quota, please check your plan and billing details.",
        "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                     "violations": [{"quotaId": "GenerateContentPaidTierInputTokensPerModelPerMinute"}]}]}})
    assert classify_gemini_429(body, {}) == "quota_exhausted"


def test_true_per_minute_limit_without_billing_wording_is_rate_limited():
    body = json.dumps({"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
        "message": "Quota exceeded for metric generate_content_requests, limit per minute. Please retry in 40s."}})
    assert classify_gemini_429(body, {}) == "rate_limited"


def test_quota_message_wins_over_retry_after_header():
    assert classify_gemini_429(QUOTA_BODY, {"Retry-After": "20"}) == "quota_exhausted"


def test_retry_after_header_alone_means_temporary_rate_limit():
    assert classify_gemini_429("Too many requests.", {"Retry-After": "20"}) == "rate_limited"


def test_per_minute_limit_is_temporary_even_with_quota_wording():
    body = "Quota exceeded for metric generate_requests per minute."
    assert classify_gemini_429(body, {}) == "rate_limited"


def test_unknown_429_defaults_to_temporary_not_quota():
    assert classify_gemini_429("", {}) == "rate_limited"


# ── Gemini adapter: 429 raises once, no retry, no key leakage ───────────────

class _FakeResponse:
    def __init__(self, status, text, headers=None):
        self.status_code = status
        self.text = text
        self.headers = headers or {}


def _fake_client(monkeypatch, status, body, calls):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, **kwargs):
            calls.append(url)
            return _FakeResponse(status, body)

    monkeypatch.setattr(llm_adapter.httpx, "AsyncClient", FakeClient)


@pytest.mark.parametrize("body,code,message", [
    (QUOTA_BODY, "quota_exhausted", QUOTA_MSG),
    (RATE_BODY, "rate_limited", RATE_MSG),
])
def test_gemini_429_raises_typed_error_without_retry(monkeypatch, body, code, message):
    calls = []
    _fake_client(monkeypatch, 429, body, calls)
    adapter = GeminiAdapter(api_key=FAKE_KEY)
    with pytest.raises(LLMProviderError) as info:
        asyncio.run(adapter.call_async("hello"))
    assert info.value.code == code
    assert info.value.provider == "gemini"
    assert str(info.value) == message
    assert len(calls) == 1, "a 429 must not be retried against another endpoint"
    assert "v1beta" in calls[0]


def test_gemini_429_message_never_contains_the_key(monkeypatch):
    calls = []
    _fake_client(monkeypatch, 429, QUOTA_BODY, calls)
    with pytest.raises(LLMProviderError) as info:
        asyncio.run(GeminiAdapter(api_key=FAKE_KEY).call_async("hello"))
    assert FAKE_KEY not in str(info.value)
    assert all(FAKE_KEY not in c for c in calls), "key must travel in a header, not the URL"


# ── Missing credentials ──────────────────────────────────────────────────────

def test_missing_key_is_reported_with_its_own_code(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    adapter = GeminiAdapter(api_key=None)
    with pytest.raises(LLMProviderError) as info:
        asyncio.run(adapter.call_async("hello"))
    assert info.value.code == "missing_key"
    assert str(info.value) == MISSING_MSG


def test_blank_key_counts_as_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(LLMProviderError) as info:
        asyncio.run(GeminiAdapter(api_key="   ").call_async("hello"))
    assert info.value.code == "missing_key"


# ── Generator: explicit failure, consent offer, no silent switch ─────────────

class _Stub:
    def __init__(self, name, error=None, reply=""):
        self.name = name
        self._error = error
        self._reply = reply
        self.calls = 0

    async def call_async(self, prompt, max_tokens=500):
        self.calls += 1
        if self._error:
            raise self._error
        return self._reply


REPLY = '```json\n[{"title": "Add subtracts", "steps": ["add(5,2)"], "expected": "3", "mutation_ids": ["M0001"]}]\n```'


def _project(tmp_path):
    project = tmp_path / "proj"
    (project / "qamill-reports").mkdir(parents=True)
    source = project / "calc.py"
    source.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    import mutation_gaps
    mutation_gaps.write_gap_file(str(project), str(source), "job", 2, 1, [{
        "mutant_id": "M0001", "operator": "AOR", "function": "add", "line": 2,
        "change": "+ -> -", "original_code": "return a + b", "mutated_code": "return a - b",
        "priority": "high", "why_survived": "x", "missing_assertion": "y", "expected_behaviour": "z"}])
    return project, source


def _run(gen, source):
    return asyncio.run(gen.generate_manual_tests(str(source), gap_driven=True))


@pytest.mark.parametrize("error,code,message", [
    (LLMProviderError("gemini", "quota_exhausted", QUOTA_MSG), "quota_exhausted", QUOTA_MSG),
    (LLMProviderError("gemini", "rate_limited", RATE_MSG), "rate_limited", RATE_MSG),
    (LLMProviderError("gemini", "missing_key", MISSING_MSG), "missing_key", MISSING_MSG),
])
def test_provider_error_is_reported_with_exact_message(tmp_path, monkeypatch, error, code, message):
    monkeypatch.setattr(llm_adapter, "ollama_status", lambda *a, **k: {"available": False})
    project, source = _project(tmp_path)
    primary = _Stub("gemini", error=error)
    result = _run(tg.TestGenerator(primary, str(project)), source)
    assert result["success"] is False
    assert result["message"] == message
    assert result["error_code"] == code
    assert result["provider"] == "gemini"


def test_no_silent_switch_to_ollama_even_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_adapter, "ollama_status", lambda *a, **k: {"available": True})
    project, source = _project(tmp_path)
    primary = _Stub("gemini", error=LLMProviderError("gemini", "quota_exhausted", QUOTA_MSG))
    fallback = _Stub("inhouse", reply=REPLY)  # must never be called
    gen = tg.TestGenerator(primary, str(project))  # no fallback configured
    result = _run(gen, source)
    assert result["success"] is False
    assert fallback.calls == 0
    assert result["provider"] == "gemini", "the configured provider stays the one in use"
    assert result["offer_ollama"] is True, "the user is offered Ollama, not switched to it"


def test_offer_ollama_is_false_when_ollama_not_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_adapter, "ollama_status", lambda *a, **k: {"available": False})
    project, source = _project(tmp_path)
    primary = _Stub("gemini", error=LLMProviderError("gemini", "rate_limited", RATE_MSG))
    result = _run(tg.TestGenerator(primary, str(project)), source)
    assert result["offer_ollama"] is False


def test_ollama_is_never_offered_to_itself(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_adapter, "ollama_status", lambda *a, **k: {"available": True})
    project, source = _project(tmp_path)
    primary = _Stub("inhouse", error=LLMProviderError("ollama", "rate_limited", RATE_MSG))
    result = _run(tg.TestGenerator(primary, str(project)), source)
    assert result["offer_ollama"] is False


def test_non_provider_errors_keep_existing_behaviour(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_adapter, "ollama_status", lambda *a, **k: {"available": True})
    project, source = _project(tmp_path)
    primary = _Stub("gemini", error=RuntimeError("connection reset"))
    result = _run(tg.TestGenerator(primary, str(project)), source)
    assert result["success"] is False
    assert result["error_code"] is None
    assert result["offer_ollama"] is False


def test_success_path_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_adapter, "ollama_status", lambda *a, **k: {"available": True})
    project, source = _project(tmp_path)
    result = _run(tg.TestGenerator(_Stub("gemini", reply=REPLY), str(project)), source)
    assert result["success"] is True
    assert result["cases"][0]["mutation_ids"] == ["M0001"]


# ── Ollama availability check ────────────────────────────────────────────────

def test_ollama_status_reports_unreachable_without_raising(monkeypatch):
    def boom(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(llm_adapter.httpx, "get", boom)
    assert llm_adapter.ollama_status()["available"] is False


def test_ollama_status_requires_configured_model(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "nomic-embed-text:latest"}]}
    monkeypatch.setattr(llm_adapter.httpx, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(llm_adapter, "create_adapter", lambda *a, **k: type("A", (), {"model": "llama3.1:8b"})())
    assert llm_adapter.ollama_status()["available"] is False


def test_ollama_status_true_when_model_installed(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "llama3.1:8b"}]}
    monkeypatch.setattr(llm_adapter.httpx, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(llm_adapter, "create_adapter", lambda *a, **k: type("A", (), {"model": "llama3.1:8b"})())
    assert llm_adapter.ollama_status()["available"] is True
