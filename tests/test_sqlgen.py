from app.sqlgen import build_user_prompt, extract_sql, make_sql_generator


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        return self.reply


def test_extract_plain():
    assert extract_sql("SELECT 1") == "SELECT 1"


def test_extract_fenced():
    assert extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"
    assert extract_sql("Here:\n```\nSELECT 2\n```\nDone") == "SELECT 2"


def test_prompt_contains_schema_question_feedback():
    p = build_user_prompt("how many orders", "Table orders", "Database error: boom")
    assert "Table orders" in p and "how many orders" in p and "Database error: boom" in p
    assert "Write a corrected query" in p


def test_prompt_without_feedback():
    assert "corrected" not in build_user_prompt("q", "s", None)


def test_generator_uses_llm_and_strips_fences():
    llm = FakeLLM("```sql\nSELECT count(*) FROM orders\n```")
    gen = make_sql_generator(llm)
    assert gen("how many orders", "Table orders", None) == "SELECT count(*) FROM orders"
    system, user = llm.calls[0]
    assert "PostgreSQL" in system and "Table orders" in user
