import httpx
import pytest

from app.openai_compat import OpenAICompatLLM


class FakeResponse:
    def __init__(self, status=200, headers=None, content="SELECT 1"):
        self.status_code = status
        self.headers = headers or {}
        self.text = "err"
        self._content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("x", request=None, response=None)

    def json(self):
        return {"choices": [{"message": {"role": "assistant", "content": self._content}}]}


def test_gemini_request_and_parse(monkeypatch):
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, json=json, headers=headers)
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QP_LLM_MODEL", "some-model")
    assert OpenAICompatLLM("gemini").complete("sys", "user") == "SELECT 1"
    assert sent["url"] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer k"
    assert sent["json"]["model"] == "some-model" and sent["json"]["temperature"] == 0
    assert [m["role"] for m in sent["json"]["messages"]] == ["system", "user"]


def test_retries_on_429(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(1)
        return FakeResponse(429, {"retry-after": "0"}) if len(calls) == 1 else FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert OpenAICompatLLM("groq").complete("s", "u") == "SELECT 1"
    assert len(calls) == 2


def test_retries_on_503(monkeypatch):
    calls = []
    monkeypatch.setattr("app.openai_compat.time.sleep", lambda s: None)

    def fake_post(url, json, headers, timeout):
        calls.append(1)
        return FakeResponse(503) if len(calls) < 3 else FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert OpenAICompatLLM("gemini").complete("s", "u") == "SELECT 1"
    assert len(calls) == 3


def test_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr("app.openai_compat.time.sleep", lambda s: None)
    monkeypatch.setattr(httpx, "post", lambda url, json, headers, timeout: FakeResponse(503))
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with pytest.raises(RuntimeError):
        OpenAICompatLLM("gemini").complete("s", "u")


def test_missing_key_and_unknown_provider(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAICompatLLM("gemini")
    with pytest.raises(ValueError):
        OpenAICompatLLM("nope")


def test_empty_reply_is_an_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, json, headers, timeout: FakeResponse(content=None))
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    with pytest.raises(RuntimeError):
        OpenAICompatLLM("openrouter").complete("s", "u")


def test_factory_picks_gemini(monkeypatch):
    from app.agent import factory

    monkeypatch.setenv("QP_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    factory._generator.cache_clear()
    monkeypatch.setattr(httpx, "post", lambda url, json, headers, timeout: FakeResponse())
    assert factory._generator()("q", "Table t", None) == "SELECT 1"
    factory._generator.cache_clear()