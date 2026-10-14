"""Question -> SQL -> validate -> execute -> analyze, with error-feedback retries."""
from __future__ import annotations

from pathlib import Path

from app.agent.types import (
    AgentResult,
    Attempt,
    SchemaProvider,
    SqlExecutor,
    SqlGenerator,
    SqlValidator,
)
from app.analysis import analyze

PREVIEW_ROWS = 50
MAX_ANALYSIS_ROWS = 5000


class QueryPilotAgent:
    def __init__(
        self,
        schema_provider: SchemaProvider,
        generate_sql: SqlGenerator,
        validate: SqlValidator,
        execute: SqlExecutor,
        max_retries: int = 2,
        chart_dir: Path = Path("charts"),
    ) -> None:
        self.schema_provider = schema_provider
        self.generate_sql = generate_sql
        self.validate = validate
        self.execute = execute
        self.max_retries = max_retries
        self.chart_dir = chart_dir

    def ask(self, question: str) -> AgentResult:
        schema = self.schema_provider()
        attempts: list[Attempt] = []
        feedback: str | None = None
        last_error = "unknown error"

        for _ in range(self.max_retries + 1):
            sql = self.generate_sql(question, schema, feedback)

            outcome = self.validate(sql)
            if not outcome.ok:
                last_error = outcome.error or "rejected by validator"
                attempts.append(Attempt(sql, "validation", last_error))
                feedback = f"Previous SQL:\n{sql}\nRejected by validator: {last_error}"
                continue

            final_sql = outcome.sql or sql
            try:
                columns, rows = self.execute(final_sql)
            except Exception as exc:  # database errors go back to the model
                last_error = str(exc)
                attempts.append(Attempt(final_sql, "execution", last_error))
                feedback = f"Previous SQL:\n{final_sql}\nDatabase error: {last_error}"
                continue

            attempts.append(Attempt(final_sql, "ok"))
            analysis = analyze(columns, rows[:MAX_ANALYSIS_ROWS], self.chart_dir)
            return AgentResult(
                ok=True,
                question=question,
                sql=final_sql,
                columns=list(columns),
                preview_rows=[list(r) for r in rows[:PREVIEW_ROWS]],
                total_rows=len(rows),
                analysis=analysis,
                attempts=attempts,
            )

        return AgentResult(
            ok=False,
            question=question,
            sql=attempts[-1].sql if attempts else None,
            attempts=attempts,
            error=f"Failed after {len(attempts)} attempts. Last error: {last_error}",
        )
