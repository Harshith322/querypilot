import pytest

from app.validator import validate_sql

TABLES = {"orders", "order_items", "customers"}


def ok(sql, **kw):
    out = validate_sql(sql, TABLES, **kw)
    assert out.ok, out.error
    return out.sql


def bad(sql):
    out = validate_sql(sql, TABLES)
    assert not out.ok
    return out.error


def test_select_gets_limit():
    assert ok("SELECT order_id FROM orders").endswith("LIMIT 1000")


def test_trailing_semicolon_ok():
    assert "LIMIT" in ok("SELECT 1 FROM orders;")


def test_large_limit_is_capped():
    assert ok("SELECT * FROM orders LIMIT 999999", max_rows=100).endswith("LIMIT 100")


def test_small_limit_kept():
    assert ok("SELECT * FROM orders LIMIT 5").endswith("LIMIT 5")


def test_cte_allowed():
    ok("WITH t AS (SELECT order_id FROM orders) SELECT * FROM t")


def test_union_and_join_allowed():
    ok("SELECT order_id FROM orders UNION SELECT order_id FROM order_items")
    ok("SELECT o.order_id FROM orders o JOIN customers c ON c.customer_id = o.customer_id")


@pytest.mark.parametrize("sql", [
    "INSERT INTO orders VALUES (1)",
    "UPDATE orders SET order_status = 'x'",
    "DELETE FROM orders",
    "DROP TABLE orders",
    "TRUNCATE orders",
    "ALTER TABLE orders ADD COLUMN x int",
    "CREATE TABLE x (a int)",
    "COPY orders TO '/tmp/x'",
    "SET statement_timeout = 0",
    "SELECT * INTO newtable FROM orders",
    "SELECT * FROM orders FOR UPDATE",
    "GRANT ALL ON orders TO public",
])
def test_non_select_rejected(sql):
    bad(sql)


def test_multiple_statements_rejected():
    assert "one statement" in bad("SELECT 1 FROM orders; DROP TABLE orders").lower()


def test_dml_inside_cte_rejected():
    bad("WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d")


def test_unknown_table_rejected_with_hint():
    err = bad("SELECT * FROM payments")
    assert "Unknown table: payments" in err and "orders" in err


@pytest.mark.parametrize("sql", [
    "SELECT * FROM pg_catalog.pg_user",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM pg_shadow",
    "SELECT * FROM public.pg_user",
])
def test_system_catalogs_rejected(sql):
    bad(sql)


@pytest.mark.parametrize("sql", [
    "SELECT pg_sleep(10)",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT current_setting('server_version')",
    "SELECT dblink('x','y')",
    "SELECT set_config('a','b',false)",
])
def test_dangerous_functions_rejected(sql):
    bad(sql)


def test_comment_cannot_hide_statement():
    sql = "SELECT order_id FROM orders /* ; DROP TABLE orders */"
    out = ok(sql)
    assert "DROP" not in out and "/*" not in out


def test_syntax_error_message():
    assert not validate_sql("SELECT FROM WHERE", TABLES).ok
    assert not validate_sql("SELEC order_id FROM orders", TABLES).ok


def test_empty():
    assert not validate_sql("   ", TABLES).ok
