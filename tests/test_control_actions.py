"""
Tests for backend/tools/control_actions.py (SPEC.md §4, §4c, §3a).

Tests cover:
  - ask_clarification: correct structure, reasoning accepted per §3a
  - flag_thin_finding: correct structure, sample_size coercion, reasoning per §3a
  - final_answer: correct structure, confidence enum validation (§4c),
    chart_ref passthrough, reasoning per §3a
  - _VALID_CONFIDENCE structural check
"""

import pytest

from backend.tools.control_actions import (
    ClarificationResult,
    FinalAnswerResult,
    ThinFlagResult,
    _VALID_CONFIDENCE,
    ask_clarification,
    final_answer,
    flag_thin_finding,
)


REASONING = "Taking this action because the question needs clarification."


# ── ask_clarification ──────────────────────────────────────────────────────────

def test_ask_clarification_action_field() -> None:
    res = ask_clarification("Which year do you mean?", REASONING)
    assert res["action"] == "ask_clarification"


def test_ask_clarification_question_passthrough() -> None:
    q = "Are you asking about films you watched or films you rated?"
    res = ask_clarification(q, REASONING)
    assert res["question"] == q


def test_ask_clarification_reasoning_accepted() -> None:
    """§3a: reasoning is required in signature; does not affect return value."""
    res_a = ask_clarification("Q?", "reasoning A")
    res_b = ask_clarification("Q?", "completely different reasoning B")
    assert res_a["question"] == res_b["question"]
    assert res_a["action"] == res_b["action"]


def test_ask_clarification_returns_only_expected_keys() -> None:
    res = ask_clarification("Q?", REASONING)
    assert set(res.keys()) == {"action", "question"}


# ── flag_thin_finding ──────────────────────────────────────────────────────────

def test_flag_thin_finding_action_field() -> None:
    res = flag_thin_finding("You rated westerns highly", 3, REASONING)
    assert res["action"] == "flag_thin_finding"


def test_flag_thin_finding_passthrough() -> None:
    res = flag_thin_finding("Pattern based on 2 films", 2, REASONING)
    assert res["finding"] == "Pattern based on 2 films"
    assert res["sample_size"] == 2


def test_flag_thin_finding_sample_size_coerced_to_int() -> None:
    """sample_size coerced to int in case LLM passes a float."""
    res = flag_thin_finding("Some finding", 4.0, REASONING)  # type: ignore[arg-type]
    assert isinstance(res["sample_size"], int)
    assert res["sample_size"] == 4


def test_flag_thin_finding_reasoning_accepted() -> None:
    res = flag_thin_finding("Finding", 1, "any reasoning")
    assert res["action"] == "flag_thin_finding"


def test_flag_thin_finding_returns_only_expected_keys() -> None:
    res = flag_thin_finding("F", 5, REASONING)
    assert set(res.keys()) == {"action", "finding", "sample_size"}


# ── final_answer ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("confidence", ["high", "medium", "low"])
def test_final_answer_valid_confidence(confidence: str) -> None:
    res = final_answer("You watch mostly drama.", "chart-abc", confidence, REASONING)
    assert res["action"] == "final_answer"
    assert res["confidence"] == confidence
    assert res["error"] is None


def test_final_answer_summary_and_chart_ref_passthrough() -> None:
    res = final_answer("Drama dominates.", "chart-xyz-123", "high", REASONING)
    assert res["summary"] == "Drama dominates."
    assert res["chart_ref"] == "chart-xyz-123"


def test_final_answer_empty_chart_ref_allowed() -> None:
    """chart_ref can be empty string if no chart was produced."""
    res = final_answer("No chart needed.", "", "medium", REASONING)
    assert res["chart_ref"] == ""
    assert res["error"] is None


def test_final_answer_invalid_confidence_returns_error() -> None:
    """Invalid confidence value — error is set, action still present for harness."""
    res = final_answer("Summary.", "", "very_high", REASONING)
    assert res["action"] == "final_answer"
    assert res["error"] is not None
    assert "very_high" in res["error"]
    assert res["confidence"] == "very_high"   # preserved as-is so harness can log it


@pytest.mark.parametrize("bad_confidence", ["", "HIGH", "High", "unsure", "none"])
def test_final_answer_various_invalid_confidences(bad_confidence: str) -> None:
    res = final_answer("S", "", bad_confidence, REASONING)
    assert res["error"] is not None


def test_final_answer_reasoning_accepted() -> None:
    """§3a: reasoning required in signature, does not affect output."""
    res = final_answer("S", "", "high", "any reasoning string")
    assert res["action"] == "final_answer"
    assert res["error"] is None


def test_final_answer_returns_expected_keys() -> None:
    res = final_answer("S", "", "low", REASONING)
    assert set(res.keys()) == {"action", "summary", "chart_ref", "confidence", "error"}


# ── _VALID_CONFIDENCE structural check (§4c) ───────────────────────────────────

def test_valid_confidence_matches_spec() -> None:
    """Structural check: the allowed set is exactly what §4c specifies."""
    assert _VALID_CONFIDENCE == {"high", "medium", "low"}
