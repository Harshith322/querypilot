"""Turn raw query results (columns + rows) into a typed DataFrame and a profile."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Sequence

import pandas as pd


def build_frame(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> pd.DataFrame:
    """Build a DataFrame from DB output and fix types Postgres drivers return.

    Decimal -> float, date/datetime objects -> datetime64.
    """
    df = pd.DataFrame(list(rows), columns=list(columns))
    for col in df.columns:
        s = df[col]
        if s.dtype != object:
            continue
        first = next((v for v in s if v is not None), None)
        if isinstance(first, Decimal):
            df[col] = pd.to_numeric(s.map(lambda v: None if v is None else float(v)))
        elif isinstance(first, (dt.date, dt.datetime)):
            df[col] = pd.to_datetime(s)
    return df


def column_kinds(df: pd.DataFrame) -> dict[str, str]:
    """Classify each column as numeric, time or category."""
    kinds: dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_bool_dtype(s):
            kinds[col] = "category"
        elif pd.api.types.is_numeric_dtype(s):
            kinds[col] = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            kinds[col] = "time"
        else:
            kinds[col] = "category"
    return kinds


def profile(df: pd.DataFrame) -> dict[str, Any]:
    """Small, JSON-safe profile the agent can read."""
    kinds = column_kinds(df)
    out: dict[str, Any] = {"row_count": int(len(df)), "columns": {}}
    for col in df.columns:
        s = df[col]
        info: dict[str, Any] = {
            "kind": kinds[col],
            "nulls": int(s.isna().sum()),
            "distinct": int(s.nunique(dropna=True)),
        }
        if kinds[col] == "numeric" and s.notna().any():
            info.update(
                min=float(s.min()),
                max=float(s.max()),
                mean=float(s.mean()),
                median=float(s.median()),
            )
        elif kinds[col] == "time" and s.notna().any():
            info.update(min=str(s.min()), max=str(s.max()))
        elif kinds[col] == "category" and s.notna().any():
            top = s.value_counts().head(3)
            info["top_values"] = {str(k): int(v) for k, v in top.items()}
        out["columns"][col] = info
    return out
