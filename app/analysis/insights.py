"""Deterministic plain-English insights. Every number comes from the data."""
from __future__ import annotations

import pandas as pd

from app.analysis.charts import ChartSpec


def build_insights(df: pd.DataFrame, spec: ChartSpec) -> list[str]:
    notes: list[str] = [f"{len(df)} rows returned."]
    nulls = int(df.isna().sum().sum())
    if nulls:
        notes.append(f"{nulls} null values present in the result.")

    if spec.kind == "bar":
        d = df.sort_values(spec.y, ascending=False)
        top, bottom = d.iloc[0], d.iloc[-1]
        notes.append(f"Highest {spec.y}: {top[spec.x]} ({top[spec.y]:,.2f}).")
        notes.append(f"Lowest {spec.y}: {bottom[spec.x]} ({bottom[spec.y]:,.2f}).")
        total = d[spec.y].sum()
        if total > 0 and (d[spec.y] >= 0).all():
            share = top[spec.y] / total * 100
            notes.append(f"{top[spec.x]} accounts for {share:.1f}% of the total.")
    elif spec.kind == "line":
        d = df.sort_values(spec.x)
        first, last = d[spec.y].iloc[0], d[spec.y].iloc[-1]
        if first != 0:
            change = (last - first) / abs(first) * 100
            notes.append(f"{spec.y} moved {change:+.1f}% from first to last period.")
        peak = d.loc[d[spec.y].idxmax()]
        notes.append(f"Peak {spec.y}: {peak[spec.y]:,.2f} at {peak[spec.x]}.")
    elif spec.kind == "scatter":
        r = df[spec.x].corr(df[spec.y])
        if pd.notna(r):
            notes.append(f"Correlation between {spec.x} and {spec.y}: r = {r:.2f}.")
    elif spec.kind == "hist":
        s = df[spec.x].dropna()
        notes.append(
            f"{spec.x}: mean {s.mean():,.2f}, median {s.median():,.2f}, "
            f"min {s.min():,.2f}, max {s.max():,.2f}."
        )
    return notes
