"""Read-only query execution. Three layers: read-only role, read-only transaction, timeout."""
from __future__ import annotations

from typing import Any, Sequence

import psycopg

from app.config import get_settings


def run_readonly(
    sql: str, dsn: str | None = None, timeout_ms: int | None = None
) -> tuple[list[str], list[Sequence[Any]]]:
    s = get_settings()
    dsn = dsn or s.readonly_dsn
    timeout_ms = timeout_ms or s.statement_timeout_ms
    options = f"-c statement_timeout={int(timeout_ms)} -c default_transaction_read_only=on"
    with psycopg.connect(dsn, options=options) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description is None:
                return [], []
            columns = [d.name for d in cur.description]
            return columns, cur.fetchall()
