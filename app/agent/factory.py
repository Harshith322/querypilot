"""Wires steps 1 to 4 into the agent. Needs a database, plus a hosted-provider key, ANTHROPIC_API_KEY or a local Ollama."""
from __future__ import annotations

import os
from functools import lru_cache

from app.agent.orchestrator import QueryPilotAgent
from app.agent.types import ValidationOutcome
from app.config import get_settings
from app.db import run_readonly
from app.llm import AnthropicLLM, OllamaLLM
from app.openai_compat import PRESETS, OpenAICompatLLM
from app.schema import SchemaInfo, format_schema, load_schema
from app.sqlgen import make_sql_generator
from app.validator import validate_sql


@lru_cache(maxsize=1)
def _schema_info() -> SchemaInfo:
    return load_schema(get_settings().readonly_dsn)


@lru_cache(maxsize=1)
def _generator():
    # QP_LLM_PROVIDER=gemini | groq | openrouter | ollama; anything else uses Anthropic
    provider = os.getenv("QP_LLM_PROVIDER", "anthropic")
    if provider in PRESETS:
        return make_sql_generator(OpenAICompatLLM(provider))
    if provider == "ollama":
        return make_sql_generator(OllamaLLM())
    return make_sql_generator(AnthropicLLM())


def _schema_provider() -> str:
    return format_schema(_schema_info())


def _generate_sql(question: str, schema: str, feedback: str | None) -> str:
    return _generator()(question, schema, feedback)


def _validate(sql: str) -> ValidationOutcome:
    return validate_sql(sql, _schema_info().table_names(), get_settings().max_rows)


def _execute(sql: str):
    return run_readonly(sql)


def build_agent() -> QueryPilotAgent:
    return QueryPilotAgent(_schema_provider, _generate_sql, _validate, _execute)