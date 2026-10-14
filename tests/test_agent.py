from app.agent import QueryPilotAgent, ValidationOutcome
from app.agent.tools import TOOL_SPEC, run_tool

SCHEMA = "table sales(category text, amount numeric)"
ROWS = [("A", 50), ("B", 30), ("C", 20)]


def make_agent(tmp_path, sqls, validations=None, executions=None, max_retries=2):
    calls = {"feedback": [], "gen": 0}

    def gen(question, schema, feedback):
        calls["feedback"].append(feedback)
        sql = sqls[min(calls["gen"], len(sqls) - 1)]
        calls["gen"] += 1
        return sql

    def validate(sql):
        if validations:
            return validations(sql)
        return ValidationOutcome(True, sql + " LIMIT 1000")

    def execute(sql):
        if executions:
            return executions(sql)
        return ["category", "amount"], ROWS

    agent = QueryPilotAgent(lambda: SCHEMA, gen, validate, execute, max_retries, tmp_path)
    return agent, calls


def test_success_first_try(tmp_path):
    agent, calls = make_agent(tmp_path, ["SELECT 1"])
    res = agent.ask("sales by category")
    assert res.ok and res.total_rows == 3
    assert res.sql.endswith("LIMIT 1000")
    assert res.analysis.chart_type == "bar"
    assert len(res.attempts) == 1 and calls["feedback"] == [None]


def test_validation_failure_then_success(tmp_path):
    def validations(sql):
        if "DROP" in sql:
            return ValidationOutcome(False, error="only SELECT allowed")
        return ValidationOutcome(True, sql)

    agent, calls = make_agent(tmp_path, ["DROP TABLE x", "SELECT 1"], validations)
    res = agent.ask("q")
    assert res.ok and len(res.attempts) == 2
    assert res.attempts[0].stage == "validation"
    assert "only SELECT allowed" in calls["feedback"][1]


def test_execution_error_then_success(tmp_path):
    state = {"n": 0}

    def executions(sql):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError('column "amt" does not exist')
        return ["category", "amount"], ROWS

    agent, calls = make_agent(tmp_path, ["SELECT amt", "SELECT amount"], executions=executions)
    res = agent.ask("q")
    assert res.ok and res.attempts[0].stage == "execution"
    assert 'column "amt" does not exist' in calls["feedback"][1]


def test_gives_up_after_retries(tmp_path):
    agent, _ = make_agent(
        tmp_path, ["bad"], validations=lambda s: ValidationOutcome(False, error="nope")
    )
    res = agent.ask("q")
    assert not res.ok and len(res.attempts) == 3
    assert "Failed after 3 attempts" in res.error


def test_retry_cap_is_respected(tmp_path):
    agent, calls = make_agent(
        tmp_path, ["bad"], validations=lambda s: ValidationOutcome(False, error="x"), max_retries=0
    )
    agent.ask("q")
    assert calls["gen"] == 1


def test_preview_is_truncated(tmp_path):
    big = [("c%d" % i, i) for i in range(120)]
    agent, _ = make_agent(tmp_path, ["SELECT 1"], executions=lambda s: (["category", "amount"], big))
    res = agent.ask("q")
    assert res.total_rows == 120 and len(res.preview_rows) == 50


def test_empty_result(tmp_path):
    agent, _ = make_agent(tmp_path, ["SELECT 1"], executions=lambda s: (["category", "amount"], []))
    res = agent.ask("q")
    assert res.ok and res.analysis.insights == ["No rows returned."]


def test_tool_dispatch(tmp_path):
    agent, _ = make_agent(tmp_path, ["SELECT 1"])
    out = run_tool(agent, TOOL_SPEC["name"], {"question": "sales"})
    assert out["ok"] and out["analysis"]["chart_type"] == "bar"
    assert not run_tool(agent, "other", {})["ok"]
    assert not run_tool(agent, TOOL_SPEC["name"], {"question": " "})["ok"]
