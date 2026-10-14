"""Question -> SQL text using an LLM. Feedback from a failed attempt is added to the prompt."""
from __future__ import annotations

import re
from typing import Callable

from app.llm import LLM
from app.prompts import DOMAIN_NOTES, SYSTEM_PROMPT

FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_sql(text: str) -> str:
    m = FENCE.search(text)
    return (m.group(1) if m else text).strip()


def build_user_prompt(question: str, schema: str, feedback: str | None) -> str:
    parts = [f"Database schema:\n{schema}", DOMAIN_NOTES, f"Question: {question}"]
    if feedback:
        parts.append(f"{feedback}\nWrite a corrected query.")
    return "\n\n".join(parts)


def make_sql_generator(llm: LLM) -> Callable[[str, str, str | None], str]:
    def generate(question: str, schema: str, feedback: str | None) -> str:
        raw = llm.complete(SYSTEM_PROMPT, build_user_prompt(question, schema, feedback))
        return extract_sql(raw)

    return generate
