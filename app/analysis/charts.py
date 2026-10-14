"""Pick a chart type from the result shape and render it to a PNG."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from app.analysis.profile import column_kinds  # noqa: E402

MAX_BARS = 20


@dataclass(frozen=True)
class ChartSpec:
    kind: str  # line | bar | scatter | hist | none
    x: str | None = None
    y: str | None = None


def choose_chart(df: pd.DataFrame) -> ChartSpec:
    """Deterministic chart choice. No LLM involved."""
    if len(df) < 2:
        return ChartSpec("none")
    kinds = column_kinds(df)
    numeric = [c for c, k in kinds.items() if k == "numeric"]
    time = [c for c, k in kinds.items() if k == "time"]
    cats = [c for c, k in kinds.items() if k == "category"]

    if time and numeric:
        return ChartSpec("line", time[0], numeric[0])
    if cats and numeric:
        return ChartSpec("bar", cats[0], numeric[0])
    if len(numeric) >= 2:
        return ChartSpec("scatter", numeric[0], numeric[1])
    if len(numeric) == 1:
        return ChartSpec("hist", numeric[0])
    return ChartSpec("none")


def render_chart(df: pd.DataFrame, spec: ChartSpec, out_dir: Path) -> Path | None:
    """Render the chart and return the PNG path, or None for kind 'none'."""
    if spec.kind == "none":
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    try:
        if spec.kind == "line":
            d = df.sort_values(spec.x)
            ax.plot(d[spec.x], d[spec.y], marker="o")
            fig.autofmt_xdate()
        elif spec.kind == "bar":
            d = df.sort_values(spec.y, ascending=False).head(MAX_BARS)
            labels = d[spec.x].astype(str)
            if labels.str.len().mean() > 8:
                ax.barh(labels[::-1], d[spec.y][::-1])
            else:
                ax.bar(labels, d[spec.y])
                fig.autofmt_xdate()
        elif spec.kind == "scatter":
            ax.scatter(df[spec.x], df[spec.y])
            ax.set_ylabel(spec.y)
        elif spec.kind == "hist":
            ax.hist(df[spec.x].dropna(), bins=min(20, max(5, len(df) // 5)))
        ax.set_xlabel(spec.x or "")
        if spec.kind in ("line", "bar"):
            ax.set_ylabel(spec.y or "")
        ax.set_title(_title(spec))
        fig.tight_layout()
        path = out_dir / f"chart_{uuid.uuid4().hex[:10]}.png"
        fig.savefig(path, dpi=120)
        return path
    finally:
        plt.close(fig)


def _title(spec: ChartSpec) -> str:
    if spec.kind == "hist":
        return f"Distribution of {spec.x}"
    return f"{spec.y} by {spec.x}"
