"""Settings from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # load <project root>/.env; variables already set in the terminal take priority
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:  # python-dotenv not installed: fall back to real environment variables only
    pass


@dataclass(frozen=True)
class Settings:
    admin_dsn: str
    readonly_dsn: str
    model: str
    max_rows: int
    statement_timeout_ms: int


def get_settings() -> Settings:
    return Settings(
        admin_dsn=os.getenv("QP_ADMIN_DSN", "postgresql://postgres:postgres@localhost:5432/querypilot"),
        readonly_dsn=os.getenv("QP_READONLY_DSN", "postgresql://qp_readonly:readonly@localhost:5432/querypilot"),
        model=os.getenv("QP_MODEL", "claude-sonnet-5-5"),
        max_rows=int(os.getenv("QP_MAX_ROWS", "1000")),
        statement_timeout_ms=int(os.getenv("QP_STATEMENT_TIMEOUT_MS", "5000")),
    )