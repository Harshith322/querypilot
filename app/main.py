"""FastAPI app: POST /ask, GET /charts/{name}, GET /health, and the UI at /."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent import QueryPilotAgent
from app.examples import EXAMPLE_QUESTIONS
from app.schema import SchemaInfo

log = logging.getLogger("querypilot")

CHART_DIR = Path("charts")
STATIC_DIR = Path(__file__).parent / "static"
CHART_NAME = re.compile(r"^chart_[0-9a-f]{10}\.png$")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


PREVIEW_LIMIT = 5


def create_app(
    agent_factory: Callable[[], QueryPilotAgent] | None = None,
    chart_dir: Path = CHART_DIR,
    schema_provider: Callable[[], SchemaInfo] | None = None,
    execute: Callable | None = None,
) -> FastAPI:
    app = FastAPI(title="QueryPilot")
    state: dict = {}

    def get_schema() -> SchemaInfo:
        fn = schema_provider
        if fn is None:
            from app.agent.factory import _schema_info as fn
        return fn()

    def run(sql: str):
        fn = execute
        if fn is None:
            from app.db import run_readonly as fn
        return fn(sql)

    def get_agent() -> QueryPilotAgent:
        if "agent" not in state:
            factory = agent_factory
            if factory is None:
                from app.agent.factory import build_agent as factory
            state["agent"] = factory()
        return state["agent"]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask")
    def ask(req: AskRequest) -> dict:
        try:
            agent = get_agent()
        except NotImplementedError:
            raise HTTPException(503, "Agent is not configured. Fill in app/agent/factory.py.")
        try:
            result = agent.ask(req.question.strip())
        except Exception:
            log.exception("agent failure")
            raise HTTPException(500, "Agent failed. Check server logs.")
        payload = result.to_dict()
        analysis = payload.get("analysis")
        if analysis:
            path = analysis.get("chart_path")
            analysis["chart_url"] = f"/charts/{Path(path).name}" if path else None
            analysis.pop("chart_path", None)
        return payload

    @app.get("/examples")
    def examples() -> list[str]:
        return EXAMPLE_QUESTIONS

    @app.get("/schema")
    def schema() -> dict:
        try:
            info = get_schema()
        except Exception:
            log.exception("schema failure")
            raise HTTPException(503, "Database is not reachable.")
        if "counts" not in state:
            state["counts"] = {}
        tables = []
        for name, cols in info.tables.items():
            if name not in state["counts"]:
                try:
                    state["counts"][name] = int(run(f'SELECT count(*) FROM "{name}"')[1][0][0])
                except Exception:
                    log.exception("count failure")
                    state["counts"][name] = None
            tables.append({
                "name": name,
                "row_count": state["counts"][name],
                "columns": [
                    {"name": c.name, "type": c.type, "pk": c.is_pk, "fk": c.fk} for c in cols
                ],
            })
        return {"tables": tables}

    @app.get("/tables/{name}")
    def table_preview(name: str) -> dict:
        try:
            info = get_schema()
        except Exception:
            raise HTTPException(503, "Database is not reachable.")
        if name not in info.tables:  # allowlist, so the name is never injected into SQL
            raise HTTPException(404, "unknown table")
        columns, rows = run(f'SELECT * FROM "{name}" LIMIT {PREVIEW_LIMIT}')
        return {"name": name, "columns": columns, "rows": [list(r) for r in rows]}

    @app.get("/charts/{name}")
    def chart(name: str) -> FileResponse:
        if not CHART_NAME.match(name):
            raise HTTPException(404, "not found")
        path = chart_dir / name
        if not path.is_file():
            raise HTTPException(404, "not found")
        return FileResponse(path, media_type="image/png")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app(chart_dir=CHART_DIR)