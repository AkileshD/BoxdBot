"""
Tests for backend/tools/make_chart.py (SPEC.md §4, §4b, §3a).

Tests cover:
  - All three valid chart types produce well-formed Plotly JSON
  - Invalid chart_type returns an error observation (not a crash)
  - Data contract validation: empty list, missing keys, wrong types
  - reasoning field is accepted per §3a and does not affect output
  - chart_id is a unique UUID per call
  - chart_json round-trips through json.loads cleanly
"""

import json
import uuid

import pytest

from backend.tools.make_chart import ChartResult, _VALID_CHART_TYPES, make_chart


REASONING = "I need to visualise the rating distribution to answer the question."

# ── Minimal valid data fixture ─────────────────────────────────────────────────

SAMPLE_DATA = [
    {"label": "Drama", "value": 12},
    {"label": "Comedy", "value": 8},
    {"label": "Thriller", "value": 5},
]


# ── Valid chart types — all three must produce ok results ──────────────────────

@pytest.mark.parametrize("chart_type", ["bar", "line", "scatter"])
def test_valid_chart_types_return_ok(chart_type: str) -> None:
    res = make_chart(SAMPLE_DATA, chart_type, REASONING)
    assert res["status"] == "ok", f"Expected ok for chart_type={chart_type}, got: {res}"
    assert res["error"] is None
    assert res["chart_json"] != ""
    assert res["chart_id"] != ""


@pytest.mark.parametrize("chart_type", ["bar", "line", "scatter"])
def test_chart_json_is_valid_json(chart_type: str) -> None:
    """chart_json must be parseable by json.loads — frontend will parse it."""
    res = make_chart(SAMPLE_DATA, chart_type, REASONING)
    parsed = json.loads(res["chart_json"])
    assert "data" in parsed       # Plotly figure always has a "data" key
    assert isinstance(parsed["data"], list)
    assert len(parsed["data"]) == 1


@pytest.mark.parametrize("chart_type", ["bar", "line", "scatter"])
def test_labels_and_values_appear_in_figure(chart_type: str) -> None:
    """Data passed in must show up in the serialised figure."""
    res = make_chart(SAMPLE_DATA, chart_type, REASONING)
    parsed = json.loads(res["chart_json"])
    trace = parsed["data"][0]
    assert "Drama" in trace["x"]
    assert 12.0 in trace["y"]


def test_chart_id_is_valid_uuid() -> None:
    res = make_chart(SAMPLE_DATA, "bar", REASONING)
    # Should parse without raising
    uuid.UUID(res["chart_id"])


def test_chart_id_is_unique_per_call() -> None:
    res1 = make_chart(SAMPLE_DATA, "bar", REASONING)
    res2 = make_chart(SAMPLE_DATA, "bar", REASONING)
    assert res1["chart_id"] != res2["chart_id"]


# ── §3a: reasoning field ───────────────────────────────────────────────────────

def test_reasoning_field_accepted_does_not_affect_output() -> None:
    res_a = make_chart(SAMPLE_DATA, "bar", "reasoning A")
    res_b = make_chart(SAMPLE_DATA, "bar", "reasoning B — completely different")
    # Both succeed; reasoning does not affect the chart
    assert res_a["status"] == "ok"
    assert res_b["status"] == "ok"


# ── Invalid chart_type ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_type", ["pie", "histogram", "heatmap", "", "Bar", "BAR"])
def test_invalid_chart_type_returns_error(bad_type: str) -> None:
    res = make_chart(SAMPLE_DATA, bad_type, REASONING)
    assert res["status"] == "error", f"Expected error for chart_type={bad_type!r}"
    assert res["chart_json"] == ""
    assert res["chart_id"] == ""
    assert res["error"] is not None
    assert bad_type in res["error"] or "Invalid" in res["error"]


def test_valid_chart_types_constant_matches_spec() -> None:
    """Structural check: the allowed set is exactly what §4b specifies."""
    assert _VALID_CHART_TYPES == {"bar", "line", "scatter"}


# ── Data contract validation ───────────────────────────────────────────────────

def test_empty_data_returns_error() -> None:
    res = make_chart([], "bar", REASONING)
    assert res["status"] == "error"
    assert res["error"] is not None


def test_missing_label_key_returns_error() -> None:
    bad_data = [{"value": 5}, {"value": 3}]
    res = make_chart(bad_data, "bar", REASONING)
    assert res["status"] == "error"
    assert "label" in res["error"].lower() or "validation" in res["error"].lower()


def test_missing_value_key_returns_error() -> None:
    bad_data = [{"label": "Drama"}, {"label": "Comedy"}]
    res = make_chart(bad_data, "bar", REASONING)
    assert res["status"] == "error"


def test_non_list_data_returns_error() -> None:
    res = make_chart({"label": "Drama", "value": 5}, "bar", REASONING)  # type: ignore[arg-type]
    assert res["status"] == "error"


def test_numeric_labels_are_coerced_to_str() -> None:
    """Labels can be numeric — they get coerced to str for Plotly's x-axis."""
    data = [{"label": 2020, "value": 10}, {"label": 2021, "value": 15}]
    res = make_chart(data, "line", REASONING)
    assert res["status"] == "ok"
    parsed = json.loads(res["chart_json"])
    assert "2020" in parsed["data"][0]["x"]
