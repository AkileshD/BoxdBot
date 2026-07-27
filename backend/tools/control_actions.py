"""
Control-action tools — fixed actions dispatched by the agent loop (SPEC.md §4, §4c, §3a).

Three tools live here because they are structurally identical: each accepts args from
the LLM, performs no computation, and returns a structured dict the harness dispatches
on (§4d). None of them has drawing logic or side-effects of its own.

Tools
-----
ask_clarification(question, reasoning) -> ClarificationResult
    Pauses the agent loop and surfaces a clarifying question back to the user (§4).
    The harness emits a `clarification` SSE event on receipt (§7a).

flag_thin_finding(finding, sample_size, reasoning) -> ThinFlagResult
    Attaches a statistical-thinness caveat to a finding (§4). The harness emits a
    `thin_flag` SSE event (§7a). Sequential with final_answer.confidence — the LLM
    will have already seen this observation before it calls final_answer (§4c).

final_answer(summary, chart_ref, confidence, reasoning) -> FinalAnswerResult
    Terminal action — ends the loop (§4). confidence is a self-assessed string enum:
    "high" | "medium" | "low" (§4c). The harness emits a `final_answer` SSE event
    followed immediately by `stream_end` (§7a).

reasoning (§3a)
---------------
All three functions accept `reasoning` as a required argument per §3a. Not used
internally — read by the harness and forwarded in the SSE tool_call event.
"""

from typing import TypedDict


# ── Confidence enum (§4c) ──────────────────────────────────────────────────────

_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})


# ── Result types ───────────────────────────────────────────────────────────────

class ClarificationResult(TypedDict):
    """
    Returned by ask_clarification.
    The harness recognises action="ask_clarification" and emits a `clarification`
    SSE event with the question field (§7a).
    """
    action: str    # always "ask_clarification"
    question: str


class ThinFlagResult(TypedDict):
    """
    Returned by flag_thin_finding.
    The harness recognises action="flag_thin_finding" and emits a `thin_flag`
    SSE event (§7a). Does not end the loop — agent continues after this observation.
    """
    action: str         # always "flag_thin_finding"
    finding: str
    sample_size: int


class FinalAnswerResult(TypedDict):
    """
    Returned by final_answer.
    Terminal action — the harness ends the loop on receipt and emits `final_answer`
    then `stream_end` SSE events (§7a). confidence is one of "high"|"medium"|"low"
    (§4c), self-assessed by the LLM.
    """
    action: str        # always "final_answer"
    summary: str
    chart_ref: str     # chart_id from make_chart, or "" if no chart
    confidence: str    # "high" | "medium" | "low"
    error: str | None  # None on success; set if confidence value is invalid


# ── Public API ─────────────────────────────────────────────────────────────────

def ask_clarification(
    question: str,
    reasoning: str,
) -> ClarificationResult:
    """
    Signal that the user's question is ambiguous and surface a clarifying question.

    Parameters
    ----------
    question:
        The clarifying question to present to the user.
    reasoning:
        Required per §3a — forwarded by the harness in the SSE tool_call event.

    Returns
    -------
    ClarificationResult dict. The harness pauses the loop and emits a `clarification`
    SSE event. Never raises.
    """
    return ClarificationResult(
        action="ask_clarification",
        question=question,
    )


def flag_thin_finding(
    finding: str,
    sample_size: int,
    reasoning: str,
) -> ThinFlagResult:
    """
    Attach a statistical-thinness caveat to a finding.

    Parameters
    ----------
    finding:
        The finding that is based on a small sample.
    sample_size:
        The number of data points the finding is based on.
    reasoning:
        Required per §3a — forwarded by the harness in the SSE tool_call event.

    Returns
    -------
    ThinFlagResult dict. The loop continues after this — the harness emits a
    `thin_flag` SSE event and appends the result to history as an observation.
    The LLM will have seen this observation before it calls final_answer (§4c).
    Never raises.
    """
    return ThinFlagResult(
        action="flag_thin_finding",
        finding=finding,
        sample_size=int(sample_size),  # coerce in case LLM passes a float
    )


def final_answer(
    summary: str,
    chart_ref: str,
    confidence: str,
    reasoning: str,
) -> FinalAnswerResult:
    """
    End the agent loop and deliver the final insight.

    Parameters
    ----------
    summary:
        The short written insight that answers the user's question.
    chart_ref:
        The chart_id returned by make_chart, or "" if no chart was produced.
    confidence:
        Self-assessed quality of the answer: "high" | "medium" | "low" (§4c).
        The LLM chooses based on evidence gathered; flag_thin_finding observations
        are one input into this assessment.
    reasoning:
        Required per §3a — forwarded by the harness in the SSE tool_call event.

    Returns
    -------
    FinalAnswerResult dict. If confidence is invalid, error is set and the harness
    should treat it as a recoverable error (return the result as an observation so
    the LLM can retry with a valid value). Never raises.
    """
    if confidence not in _VALID_CONFIDENCE:
        return FinalAnswerResult(
            action="final_answer",
            summary=summary,
            chart_ref=chart_ref,
            confidence=confidence,
            error=(
                f"Invalid confidence value '{confidence}'. "
                f"Must be one of: {sorted(_VALID_CONFIDENCE)}."
            ),
        )

    return FinalAnswerResult(
        action="final_answer",
        summary=summary,
        chart_ref=chart_ref,
        confidence=confidence,
        error=None,
    )
