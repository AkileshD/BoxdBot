"""
make_chart tool — fixed, pre-tested Plotly chart generation (SPEC.md §4, §4b, §3a).

Public surface
--------------
make_chart(data, chart_type, reasoning) -> ChartResult

This tool's drawing code is fixed and pre-tested — the agent chooses *what* to plot
and the chart type; it does not write the chart code itself (§4 rationale: chart-code
variance costs more in demo reliability than it adds in value).

Data contract (§4b)
-------------------
`data` must be a list of {"label": <str|num>, "value": <int|float>} dicts.
The agent's run_pandas code is expected to produce output in this shape; the tool
schema documents this contract explicitly so the LLM knows what to produce.

chart_type enum (§4b)
----------------------
Valid values for v1: "bar" | "line" | "scatter"
Pie and histogram are explicitly out of v1 per §4b.

Return value
------------
ChartResult is a TypedDict with:
  status:     "ok" | "error"
  chart_id:   UUID string used as chart_ref in final_answer (and findings log).
              Empty string on error.
  chart_json: Plotly figure serialised to JSON string. The harness forwards this
              in the SSE observation event so the frontend can render it via
              react-plotly.js (§7). Empty string on error.
  error:      Human-readable error description, or None on success.

reasoning (§3a)
---------------
Required in every tool's arg schema per §3a. Not used by the drawing logic — read
by the harness and forwarded in the SSE tool_call event.
"""

import json
import uuid
from typing import TypedDict

import plotly.graph_objects as go


# ── Allowed chart types (§4b) ──────────────────────────────────────────────────

_VALID_CHART_TYPES = frozenset({"bar", "line", "scatter"})


# ── Result type ────────────────────────────────────────────────────────────────

class ChartResult(TypedDict):
    """
    Structured result returned to the agent (and harness) after make_chart runs.

    Fields:
      status:     "ok" | "error"
      chart_id:   UUID string used as chart_ref in final_answer / findings log.
      chart_json: Plotly figure serialised to JSON (for SSE + frontend rendering).
      error:      Error description on failure, None on success.
    """
    status: str
    chart_id: str
    chart_json: str
    error: str | None


# ── Public API ─────────────────────────────────────────────────────────────────

def make_chart(
    data: list[dict],
    chart_type: str,
    reasoning: str,
) -> ChartResult:
    """
    Build a Plotly chart from agent-supplied data.

    Parameters
    ----------
    data:
        List of {"label": ..., "value": ...} dicts (§4b data contract).
        Labels become the x-axis; values become the y-axis.
    chart_type:
        One of "bar" | "line" | "scatter" (§4b enum). Any other value
        returns an error observation.
    reasoning:
        Required per §3a — the LLM's explanation of why it is calling this tool.
        Not used by the drawing logic; forwarded by the harness in the SSE
        tool_call event.

    Returns
    -------
    ChartResult dict. Never raises.
    """
    # ── Validate chart_type ────────────────────────────────────────────────────
    if chart_type not in _VALID_CHART_TYPES:
        return ChartResult(
            status="error",
            chart_id="",
            chart_json="",
            error=(
                f"Invalid chart_type '{chart_type}'. "
                f"Valid values for v1: {sorted(_VALID_CHART_TYPES)}."
            ),
        )

    # ── Validate data shape ────────────────────────────────────────────────────
    if not isinstance(data, list) or len(data) == 0:
        return ChartResult(
            status="error",
            chart_id="",
            chart_json="",
            error="'data' must be a non-empty list of {\"label\": ..., \"value\": ...} dicts.",
        )

    try:
        labels = [str(item["label"]) for item in data]
        values = [float(item["value"]) for item in data]
    except (KeyError, TypeError, ValueError) as exc:
        return ChartResult(
            status="error",
            chart_id="",
            chart_json="",
            error=f"Data validation failed: {exc}. Each item must have 'label' and 'value' keys.",
        )

    # ── Build Plotly figure ────────────────────────────────────────────────────
    try:
        if chart_type == "bar":
            trace = go.Bar(x=labels, y=values)
        elif chart_type == "line":
            trace = go.Scatter(x=labels, y=values, mode="lines")
        elif chart_type == "scatter":
            trace = go.Scatter(x=labels, y=values, mode="markers")

        fig = go.Figure(data=[trace])
        fig.update_layout(
            margin={"l": 40, "r": 20, "t": 30, "b": 40},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        chart_id = str(uuid.uuid4())
        chart_json = fig.to_json()

    except Exception as exc:  # noqa: BLE001
        return ChartResult(
            status="error",
            chart_id="",
            chart_json="",
            error=f"Plotly figure creation failed: {exc}",
        )

    return ChartResult(
        status="ok",
        chart_id=chart_id,
        chart_json=chart_json,
        error=None,
    )
