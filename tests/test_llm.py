import httpx

from app.llm import OllamaLLM


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"role": "assistant", "content": "SELECT 1"}}


def test_ollama_request_and_parse(monkeypatch):
    sent = {}

    def fake_post(url, json, timeout):
        sent.update(url=url, json=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("QP_OLLAMA_MODEL", "qwen2.5-coder:7b")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434/")
    out = OllamaLLM().complete("sys", "user")
    assert out == "SELECT 1"
    assert sent["url"] == "http://localhost:11434/api/chat"
    body = sent["json"]
    assert body["model"] == "qwen2.5-coder:7b" and body["stream"] is False
    assert body["options"]["num_ctx"] == 8192 and body["options"]["temperature"] == 0
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_factory_picks_ollama(monkeypatch):
    from app.agent import factory

    monkeypatch.setenv("QP_LLM_PROVIDER", "ollama")
    factory._generator.cache_clear()
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: FakeResponse())
    gen = factory._generator()
    assert gen("q", "Table t", None) == "SELECT 1"
    factory._generator.cache_clear()