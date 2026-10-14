"""Hosted LLMs that speak the OpenAI chat-completions format: Gemini, Groq, OpenRouter.

Pick one with QP_LLM_PROVIDER=gemini | groq | openrouter and set that provider's key.
Optional: QP_LLM_MODEL overrides the default model, QP_LLM_BASE_URL overrides the URL.
Free-tier model names change often; if you get a 404 / model-not-found error, set QP_LLM_MODEL.
"""
from __future__ import annotations

import os
import time

# provider -> (base url, api key env var, default model)
PRESETS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-2.5-flash"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free"),
}


class OpenAICompatLLM:
    def __init__(self, provider: str, max_tokens: int = 4096) -> None:
        if provider not in PRESETS:
            raise ValueError(f"unknown provider {provider!r}, use one of {sorted(PRESETS)}")
        base, key_env, default_model = PRESETS[provider]
        self.api_key = os.getenv(key_env, "")
        if not self.api_key:
            raise RuntimeError(f"{key_env} is not set")
        self.url = os.getenv("QP_LLM_BASE_URL", base).rstrip("/") + "/chat/completions"
        self.model = os.getenv("QP_LLM_MODEL", default_model)
        # generous: some hosted models spend part of this budget on hidden reasoning
        self.max_tokens = max_tokens
        self.provider = provider

    def complete(self, system: str, user: str) -> str:
        import httpx

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        attempts = 5
        for attempt in range(attempts):
            r = httpx.post(self.url, json=body, headers=headers, timeout=60)
            # 429 = rate limit, 5xx = provider overloaded/temporary: wait and retry
            if (r.status_code == 429 or r.status_code in (500, 502, 503, 504)) and attempt < attempts - 1:
                try:
                    wait = float(r.headers.get("retry-after", 0))
                except ValueError:
                    wait = 0
                time.sleep(min(max(wait, 2 * 2**attempt), 30))  # 2, 4, 8, 16 s
                continue
            break
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"{self.provider} error {r.status_code}: {r.text[:500]}") from exc
        content = r.json()["choices"][0]["message"].get("content")
        if not content:
            raise RuntimeError(f"{self.provider} returned an empty reply (model {self.model})")
        return content