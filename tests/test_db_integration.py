import psycopg
import pytest

from app.agent import QueryPilotAgent
from app.db import run_readonly
from app.schema import format_schema, load_schema
from app.validator import validate_sql


def test_sample_data_loaded(db):
    cols, rows = run_readonly("SELECT count(*) FROM orders", dsn=db["readonly"])
    assert rows[0][0] == 300


def test_schema_introspection(db):
    info = load_schema(db["readonly"])
    assert {"orders", "order_items", "customers", "products"} <= info.table_names()
    orders = {c.name: c for c in info.tables["orders"]}
    assert orders["order_id"].is_pk
    assert orders["customer_id"].fk == "customers.customer_id"
    assert "delivered" in orders["order_status"].values


def test_schema_text_format(db):
    text = format_schema(load_schema(db["readonly"]))
    assert "Table orders" in text
    assert "FK -> customers.customer_id" in text
    assert "values:" in text and "credit_card" in text


def test_readonly_role_cannot_write(db):
    with pytest.raises(psycopg.Error):
        run_readonly("DELETE FROM orders", dsn=db["readonly"])
    with pytest.raises(psycopg.Error):
        run_readonly("CREATE TABLE evil (a int)", dsn=db["readonly"])


def test_readonly_role_cannot_write_even_with_admin_credentials(db):
    # The transaction itself is read-only, independent of the role.
    with pytest.raises(psycopg.Error):
        run_readonly("DELETE FROM orders", dsn=db["admin"])
    _, rows = run_readonly("SELECT count(*) FROM orders", dsn=db["readonly"])
    assert rows[0][0] == 300


def test_statement_timeout(db):
    with pytest.raises(psycopg.errors.QueryCanceled):
        run_readonly("SELECT pg_sleep(5)", dsn=db["readonly"], timeout_ms=300)


def test_validated_sql_runs(db):
    info = load_schema(db["readonly"])
    out = validate_sql(
        "SELECT order_status, count(*) AS n FROM orders GROUP BY 1 ORDER BY n DESC",
        info.table_names(),
    )
    assert out.ok
    cols, rows = run_readonly(out.sql, dsn=db["readonly"])
    assert cols == ["order_status", "n"] and rows


def test_agent_end_to_end_with_fake_llm(db, tmp_path):
    info = load_schema(db["readonly"])
    answers = iter([
        "SELECT order_statu, count(*) FROM orders GROUP BY 1",  # wrong column, DB error
        "SELECT order_status, count(*) AS n FROM orders GROUP BY 1",
    ])
    seen = []

    def gen(question, schema, feedback):
        seen.append(feedback)
        return next(answers)

    agent = QueryPilotAgent(
        lambda: format_schema(info),
        gen,
        lambda sql: validate_sql(sql, info.table_names()),
        lambda sql: run_readonly(sql, dsn=db["readonly"]),
        chart_dir=tmp_path,
    )
    res = agent.ask("orders by status")
    assert res.ok and len(res.attempts) == 2
    assert res.attempts[0].stage == "execution"
    assert "order_statu" in seen[1]
    assert res.analysis.chart_type == "bar"
    assert res.analysis.chart_path
