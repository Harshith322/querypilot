from fastapi.testclient import TestClient

from app.agent import QueryPilotAgent, ValidationOutcome
from app.main import create_app

ROWS = [("A", 50), ("B", 30), ("C", 20)]


def fake_agent(tmp_path, execute=None):
    return QueryPilotAgent(
        lambda: "schema",
        lambda q, s, f: "SELECT 1",
        lambda sql: ValidationOutcome(True, sql),
        execute or (lambda sql: (["category", "amount"], ROWS)),
        chart_dir=tmp_path,
    )


def client(tmp_path, **kw):
    app = create_app(lambda: fake_agent(tmp_path, **kw), chart_dir=tmp_path)
    return TestClient(app)


def test_health(tmp_path):
    assert client(tmp_path).get("/health").json() == {"status": "ok"}


def test_index_serves_ui(tmp_path):
    r = client(tmp_path).get("/")
    assert r.status_code == 200 and "QueryPilot" in r.text


def test_ask_returns_result_and_chart_url(tmp_path):
    c = client(tmp_path)
    r = c.post("/ask", json={"question": "sales by category"})
    d = r.json()
    assert r.status_code == 200 and d["ok"]
    url = d["analysis"]["chart_url"]
    assert url.startswith("/charts/chart_")
    assert "chart_path" not in d["analysis"]
    img = c.get(url)
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"


def test_ask_validates_input(tmp_path):
    c = client(tmp_path)
    assert c.post("/ask", json={"question": "hi"}).status_code == 422
    assert c.post("/ask", json={"question": "x" * 501}).status_code == 422
    assert c.post("/ask", json={}).status_code == 422


def test_agent_exception_is_500_without_leaking(tmp_path):
    # generator failure is not caught by the agent loop, so it hits the endpoint handler
    agent = fake_agent(tmp_path)
    agent.generate_sql = lambda q, s, f: (_ for _ in ()).throw(RuntimeError("secret detail"))
    c = TestClient(create_app(lambda: agent, chart_dir=tmp_path))
    r = c.post("/ask", json={"question": "sales by category"})
    assert r.status_code == 500 and "secret detail" not in r.text


def test_unconfigured_agent_is_503(tmp_path):
    def not_ready():
        raise NotImplementedError
    c = TestClient(create_app(not_ready, chart_dir=tmp_path))
    assert c.post("/ask", json={"question": "sales by category"}).status_code == 503


def test_failed_query_returns_ok_false(tmp_path):
    def bad(sql):
        raise RuntimeError("relation does not exist")
    r = client(tmp_path, execute=bad).post("/ask", json={"question": "sales by category"})
    assert r.status_code == 200 and r.json()["ok"] is False


def test_chart_path_traversal_blocked(tmp_path):
    (tmp_path / "secret.txt").write_text("x")
    c = client(tmp_path)
    for name in ["..%2Fsecret.txt", "secret.txt", "chart_zzzzzzzzzz.png", "chart_0123456789.png"]:
        assert c.get(f"/charts/{name}").status_code == 404


# ---- schema, examples and table preview ----
from app.schema import Column, SchemaInfo

INFO = SchemaInfo({
    "orders": [Column("order_id", "text", is_pk=True), Column("customer_id", "text", fk="customers.customer_id")],
    "customers": [Column("customer_id", "text", is_pk=True)],
})


def db_client(tmp_path, calls=None):
    def fake_execute(sql):
        if calls is not None:
            calls.append(sql)
        if sql.startswith("SELECT count"):
            return ["count"], [(42,)]
        return ["order_id", "customer_id"], [("o1", "c1"), ("o2", "c2")]

    app = create_app(
        lambda: fake_agent(tmp_path), chart_dir=tmp_path,
        schema_provider=lambda: INFO, execute=fake_execute,
    )
    return TestClient(app)


def test_examples_endpoint(tmp_path):
    r = db_client(tmp_path).get("/examples")
    assert r.status_code == 200 and len(r.json()) >= 5


def test_schema_endpoint(tmp_path):
    d = db_client(tmp_path).get("/schema").json()
    orders = next(t for t in d["tables"] if t["name"] == "orders")
    assert orders["row_count"] == 42
    assert orders["columns"][0] == {"name": "order_id", "type": "text", "pk": True, "fk": None}
    assert orders["columns"][1]["fk"] == "customers.customer_id"


def test_schema_counts_are_cached(tmp_path):
    calls = []
    c = db_client(tmp_path, calls)
    c.get("/schema"); c.get("/schema")
    assert len([q for q in calls if q.startswith("SELECT count")]) == 2  # once per table


def test_table_preview(tmp_path):
    d = db_client(tmp_path).get("/tables/orders").json()
    assert d["columns"] == ["order_id", "customer_id"] and len(d["rows"]) == 2


def test_table_preview_rejects_unknown_and_injection(tmp_path):
    calls = []
    c = db_client(tmp_path, calls)
    for name in ["nope", 'orders"; DROP TABLE orders; --', "pg_user"]:
        assert c.get(f"/tables/{name}").status_code == 404
    assert calls == []


def test_schema_unreachable_is_503(tmp_path):
    def boom():
        raise RuntimeError("db down")
    app = create_app(lambda: fake_agent(tmp_path), chart_dir=tmp_path, schema_provider=boom)
    assert TestClient(app).get("/schema").status_code == 503