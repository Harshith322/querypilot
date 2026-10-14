"""Schema introspection: tables, columns, keys, and low-cardinality values for the prompt."""
from __future__ import annotations

from dataclasses import dataclass, field

import psycopg

MAX_ENUM_VALUES = 12


@dataclass
class Column:
    name: str
    type: str
    is_pk: bool = False
    fk: str | None = None  # "table.column"
    values: list[str] = field(default_factory=list)  # distinct values if low cardinality


@dataclass
class SchemaInfo:
    tables: dict[str, list[Column]]

    def table_names(self) -> set[str]:
        return set(self.tables)


COLUMNS_SQL = """
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position
"""

# pg_constraint instead of information_schema: the latter hides constraints from SELECT-only roles.
PK_SQL = """
SELECT c.conrelid::regclass::text, a.attname
FROM pg_constraint c
JOIN LATERAL unnest(c.conkey) AS k(attnum) ON true
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
WHERE c.contype = 'p' AND c.connamespace = 'public'::regnamespace
"""

FK_SQL = """
SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text, af.attname
FROM pg_constraint c
JOIN LATERAL unnest(c.conkey, c.confkey) AS k(attnum, fattnum) ON true
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = k.fattnum
WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
"""


def load_schema(dsn: str, with_values: bool = True) -> SchemaInfo:
    tables: dict[str, list[Column]] = {}
    with psycopg.connect(dsn, options="-c default_transaction_read_only=on") as conn:
        for t, c, dtype in conn.execute(COLUMNS_SQL):
            tables.setdefault(t, []).append(Column(c, dtype))
        pks = {(t.removeprefix("public."), c) for t, c in conn.execute(PK_SQL)}
        fks = {(t.removeprefix("public."), c): f"{rt.removeprefix('public.')}.{rc}"
               for t, c, rt, rc in conn.execute(FK_SQL)}
        for t, cols in tables.items():
            for col in cols:
                col.is_pk = (t, col.name) in pks
                col.fk = fks.get((t, col.name))
        if with_values:
            for t, cols in tables.items():
                for col in cols:
                    if col.type != "text" or col.is_pk or col.fk or col.name.endswith("_id"):
                        continue
                    rows = conn.execute(
                        f'SELECT "{col.name}" FROM "{t}" WHERE "{col.name}" IS NOT NULL '
                        f'GROUP BY 1 ORDER BY 1 LIMIT {MAX_ENUM_VALUES + 1}'
                    ).fetchall()
                    if 0 < len(rows) <= MAX_ENUM_VALUES:
                        col.values = [r[0] for r in rows]
    return SchemaInfo(tables)


def format_schema(info: SchemaInfo) -> str:
    lines: list[str] = []
    for table, cols in info.tables.items():
        lines.append(f"Table {table}")
        for c in cols:
            extras = []
            if c.is_pk:
                extras.append("PK")
            if c.fk:
                extras.append(f"FK -> {c.fk}")
            if c.values:
                extras.append("values: " + ", ".join(c.values))
            suffix = f" ({'; '.join(extras)})" if extras else ""
            lines.append(f"  {c.name} {c.type}{suffix}")
        lines.append("")
    return "\n".join(lines).strip()
