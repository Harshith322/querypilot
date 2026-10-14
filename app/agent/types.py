"""Shared types and the four callables the agent depends on."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from app.analysis import AnalysisResult


@dataclass
class ValidationOutcome:
    ok: bool
    sql: str | None = None  # sanitized SQL (for example with LIMIT added)
    error: str | None = None


@dataclass
class Attempt:
    sql: str
    stage: str  # validation | execution | ok
    error: str | None = None


# schema text for the prompt
SchemaProvider = Callable[[], str]
# (question, schema, feedback_from_previous_attempt) -> sql
SqlGenerator = Callable[[str, str, str | None], str]
# sql -> ValidationOutcome
SqlValidator = Callable[[str], ValidationOutcome]
# sql -> (column names, rows). Must run on the read-only role.
SqlExecutor = Callable[[str], tuple[list[str], list[Sequence[Any]]]]


@dataclass
class AgentResult:
    ok: bool
    question: str
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    preview_rows: list[list[Any]] = field(default_factory=list)
    total_rows: int = 0
    analysis: AnalysisResult | None = None
    attempts: list[Attempt] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "question": self.question,
            "sql": self.sql,
            "columns": self.columns,
            "preview_rows": self.preview_rows,
            "total_rows": self.total_rows,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "attempts": [a.__dict__ for a in self.attempts],
            "error": self.error,
        }
