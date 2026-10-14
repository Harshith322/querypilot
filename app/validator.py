"""SQL safety validation with sqlglot. The agent executes the rewritten SQL, never the raw text."""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.agent.types import ValidationOutcome

FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Merge,
    exp.Command, exp.Set, exp.Copy, exp.Into, exp.Lock, exp.Transaction, exp.Commit,
    exp.Rollback, exp.Use, exp.Grant,
)
FORBIDDEN_FUNCTIONS = {
    "dblink", "lo_import", "lo_export", "set_config", "current_setting", "query_to_xml",
    "txid_current", "version", "current_user", "session_user",
}


def _reject(msg: str) -> ValidationOutcome:
    return ValidationOutcome(ok=False, error=msg)


def validate_sql(sql: str, allowed_tables: set[str], max_rows: int = 1000) -> ValidationOutcome:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        return _reject("Empty query.")

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as e:
        return _reject(f"SQL syntax error: {str(e).splitlines()[0]}")
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return _reject("Exactly one statement is allowed.")
    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
        return _reject("Only SELECT queries are allowed.")

    bad = tree.find(*FORBIDDEN_NODES)
    if bad is not None:
        return _reject(f"Forbidden operation: {type(bad).__name__.upper()}.")

    for fn in tree.find_all(exp.Func):
        name = (fn.name if isinstance(fn, exp.Anonymous) else fn.key).lower()
        if name.startswith("pg_") or name in FORBIDDEN_FUNCTIONS:
            return _reject(f"Function not allowed: {name}.")

    cte_names = {c.alias for c in tree.find_all(exp.CTE)}
    allowed = {t.lower() for t in allowed_tables}
    for table in tree.find_all(exp.Table):
        if table.db and table.db.lower() != "public":
            return _reject(f"Schema not allowed: {table.db}. Use only tables from the schema.")
        name = table.name.lower()
        if name in cte_names:
            continue
        if name not in allowed:
            return _reject(
                f"Unknown table: {table.name}. Allowed tables: {', '.join(sorted(allowed))}."
            )

    tree = _enforce_limit(tree, max_rows)
    return ValidationOutcome(ok=True, sql=tree.sql(dialect="postgres", comments=False))


def _enforce_limit(tree: exp.Expression, max_rows: int) -> exp.Expression:
    limit = tree.args.get("limit")
    if limit is None:
        return tree.limit(max_rows)
    try:
        current = int(limit.expression.name)
    except (ValueError, AttributeError):
        return tree.limit(max_rows)
    if current > max_rows:
        return tree.limit(max_rows)
    return tree
