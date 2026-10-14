import datetime as dt
from decimal import Decimal

from app.analysis import analyze
from app.analysis.charts import choose_chart
from app.analysis.profile import build_frame


def test_decimal_and_date_are_converted():
    df = build_frame(
        ["d", "v"], [(dt.date(2025, 1, 1), Decimal("1.5")), (dt.date(2025, 2, 1), Decimal("2.5"))]
    )
    assert str(df["d"].dtype).startswith("datetime64")
    assert df["v"].dtype == float


def test_time_series_picks_line(tmp_path):
    rows = [(dt.date(2025, m, 1), m * 100) for m in range(1, 7)]
    res = analyze(["month", "revenue"], rows, tmp_path)
    assert res.chart_type == "line"
    assert res.chart_path and (tmp_path / res.chart_path.split("/")[-1]).exists()
    assert any("first to last" in i for i in res.insights)


def test_category_picks_bar(tmp_path):
    rows = [("A", 50), ("B", 30), ("C", 20)]
    res = analyze(["category", "sales"], rows, tmp_path)
    assert res.chart_type == "bar"
    assert any("50.0% of the total" in i for i in res.insights)


def test_two_numeric_picks_scatter(tmp_path):
    rows = [(1, 2), (2, 4), (3, 6), (4, 8)]
    res = analyze(["a", "b"], rows, tmp_path)
    assert res.chart_type == "scatter"
    assert any("r = 1.00" in i for i in res.insights)


def test_single_numeric_picks_hist(tmp_path):
    res = analyze(["price"], [(i,) for i in range(1, 30)], tmp_path)
    assert res.chart_type == "hist"


def test_single_row_has_no_chart(tmp_path):
    res = analyze(["total"], [(42,)], tmp_path)
    assert res.chart_type == "none" and res.chart_path is None


def test_empty_result(tmp_path):
    res = analyze(["a", "b"], [], tmp_path)
    assert res.chart_type == "none"
    assert res.insights == ["No rows returned."]


def test_nulls_reported(tmp_path):
    rows = [("A", 10), ("B", None), ("C", 5)]
    res = analyze(["cat", "val"], rows, tmp_path)
    assert any("null" in i for i in res.insights)


def test_choose_chart_text_only():
    df = build_frame(["a", "b"], [("x", "y"), ("z", "w")])
    assert choose_chart(df).kind == "none"
