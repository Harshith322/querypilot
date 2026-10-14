"""Tool definition so Claude (or the API layer) can call the agent as a tool."""
from __future__ import annotations

from typing import Any

from app.agent.orchestrator import QueryPilotAgent

TOOL_SPEC: dict[str, Any] = {
    "name": "ask_database",
    "description": (
        "Answer a business question from the PostgreSQL database. Generates read-only SQL, "
        "validates it, runs it, and returns the SQL, a result preview, statistics, "
        "insights and a chart path."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Business question in plain English."}
        },
        "required": ["question"],
    },
}


def run_tool(agent: QueryPilotAgent, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name != TOOL_SPEC["name"]:
        return {"ok": False, "error": f"unknown tool: {name}"}
    question = str(args.get("question", "")).strip()
    if not question:
        return {"ok": False, "error": "question is required"}
    return agent.ask(question).to_dict()
