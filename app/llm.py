"""Thin LLM interface so the agent can be tested with a fake and swapped for another provider."""
from __future__ import annotations

from typing import Protocol

from app.config import get_settings


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None, max_tokens: int = 1000) -> None:
        import anthropic  # reads ANTHROPIC_API_KEY from the environment

        self.client = anthropic.Anthropic()
        self.model = model or get_settings().model
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")


class OllamaLLM:
    """Local model through Ollama. No API key. Start Ollama and `ollama pull <model>` first."""

    def __init__(self, model: str | None = None, max_tokens: int = 1000) -> None:
        import os

        self.model = model or os.getenv("QP_OLLAMA_MODEL", "qwen2.5-coder:7b")
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.url = f"{host}/api/chat"
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        import httpx

        r = httpx.post(
            self.url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                # num_ctx matters: the default window is small and would cut off the schema prompt
                "options": {"temperature": 0, "num_predict": self.max_tokens, "num_ctx": 8192},
            },
            timeout=300,
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # surface Ollama's own error text (out of memory, model not found, ...)
            raise RuntimeError(f"Ollama error {r.status_code}: {r.text[:500]}") from exc
        return r.json()["message"]["content"]