"""Single entry point the agent calls after a query runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from app.analysis.charts import choose_chart, render_chart
from app.analysis.insights import build_insights
from app.analysis.profile import build_frame, profile

DEFAULT_CHART_DIR = Path("charts")


@dataclass
class AnalysisResult:
    profile: dict[str, Any]
    chart_type: str
    chart_path: str | None
    insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "chart_type": self.chart_type,
            "chart_path": self.chart_path,
            "insights": self.insights,
        }


def analyze(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    out_dir: Path = DEFAULT_CHART_DIR,
) -> AnalysisResult:
    df = build_frame(columns, rows)
    spec = choose_chart(df)
    path = render_chart(df, spec, out_dir) if len(df) else None
    return AnalysisResult(
        profile=profile(df),
        chart_type=spec.kind,
        chart_path=str(path) if path else None,
        insights=build_insights(df, spec) if len(df) else ["No rows returned."],
    )
