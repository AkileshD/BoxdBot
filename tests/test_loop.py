"""
Tests for backend/agent/loop.py (SPEC.md §3).

Mocks call_llm directly per Decision D to test loop logic without OpenAI SDK types.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backend.agent.llm_client import LLMTurn
from backend.agent.loop import run_agent_loop


@pytest.fixture
def dummy_df() -> pd.DataFrame:
    return pd.DataFrame({"Rating": [5, 4, 3]})


@patch("backend.agent.loop.call_llm")
def test_normal_multi_turn_flow(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    """Agent calls a tool, gets an observation, then returns final_answer."""
    mock_call_llm.side_effect = [
        LLMTurn(
            tool_name="run_pandas",
            arguments={"code": "result = 1", "reasoning": "checking"},
            tool_call_id="call_1",
        ),
        LLMTurn(
            tool_name="make_chart",
            arguments={"data": [{"label": "A", "value": 1}], "chart_type": "bar", "reasoning": "plot"},
            tool_call_id="call_2",
        ),
        LLMTurn(
            tool_name="final_answer",
            arguments={"summary": "Done.", "chart_ref": "c-123", "confidence": "high", "reasoning": "done"},
            tool_call_id="call_3",
        ),
    ]

    events = list(run_agent_loop("What is my average rating?", dummy_df, api_key="dummy_key"))
    
    types = [e["type"] for e in events]
    assert types == [
        "stream_start",
        "tool_call",    # run_pandas
        "observation",
        "tool_call",    # make_chart
        "observation",
        "tool_call",    # final_answer
        "final_answer",
        "stream_end",
    ]

    # Verify run_pandas call
    assert events[1]["tool_name"] == "run_pandas"
    assert events[1]["turn_index"] == 1
    
    # Verify final answer event
    final_ev = events[-2]
    assert final_ev["summary"] == "Done."
    assert final_ev["confidence"] == "high"


@patch("backend.agent.loop.call_llm")
def test_max_turn_cap_aborts_at_10(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    """Loop aborts exactly at max_turns (10) if final_answer is never reached."""
    # Always yield a run_pandas call
    mock_call_llm.return_value = LLMTurn(
        tool_name="run_pandas",
        arguments={"code": "result = 1", "reasoning": "stuck"},
        tool_call_id="call_stuck",
    )

    events = list(run_agent_loop("Q", dummy_df, api_key="dummy_key", max_turns=10))
    
    # stream_start + 10x (tool_call + observation) + error + stream_end = 23 events
    assert len(events) == 1 + 20 + 2
    
    types = [e["type"] for e in events]
    assert types[0] == "stream_start"
    assert types[-2] == "error"
    assert types[-1] == "stream_end"
    
    assert "max turns (10) exceeded" in events[-2]["message"]
    
    # 10 calls to the LLM
    assert mock_call_llm.call_count == 10


@patch("backend.agent.loop.call_llm")
def test_ask_clarification_pauses_loop(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    mock_call_llm.return_value = LLMTurn(
        tool_name="ask_clarification",
        arguments={"question": "What?", "reasoning": "ambiguous"},
        tool_call_id="call_c",
    )

    events = list(run_agent_loop("Q", dummy_df, api_key="dummy_key"))
    
    types = [e["type"] for e in events]
    assert types == [
        "stream_start",
        "tool_call",
        "clarification",
        "stream_end",
    ]
    assert events[2]["question"] == "What?"
    assert mock_call_llm.call_count == 1


@patch("backend.agent.loop.call_llm")
def test_flag_thin_finding_continues_loop(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    mock_call_llm.side_effect = [
        LLMTurn(
            tool_name="flag_thin_finding",
            arguments={"finding": "small sample", "sample_size": 2, "reasoning": "thin"},
            tool_call_id="call_f",
        ),
        LLMTurn(
            tool_name="final_answer",
            arguments={"summary": "S", "chart_ref": "", "confidence": "low", "reasoning": "done"},
            tool_call_id="call_end",
        )
    ]

    events = list(run_agent_loop("Q", dummy_df, api_key="dummy_key"))
    types = [e["type"] for e in events]
    
    assert types == [
        "stream_start",
        "tool_call",
        "thin_flag",
        "observation",   # appended to history after flag
        "tool_call",
        "final_answer",
        "stream_end",
    ]


@patch("backend.agent.loop.call_llm")
def test_call_llm_exception_surfaces_error_and_ends_stream(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    mock_call_llm.side_effect = ValueError("Network failure")

    events = list(run_agent_loop("Q", dummy_df, api_key="dummy_key"))
    types = [e["type"] for e in events]
    
    assert types == [
        "stream_start",
        "error",
        "stream_end",
    ]
    assert "LLM Call Failed: Network failure" in events[1]["message"]


@patch("backend.agent.loop.call_llm")
def test_message_history_threading(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    """Verify tool_call_id matches between assistant and tool messages."""
    mock_call_llm.side_effect = [
        LLMTurn(
            tool_name="run_pandas",
            arguments={"code": "result = 1", "reasoning": "r"},
            tool_call_id="call_MATCH",
        ),
        LLMTurn(
            tool_name="final_answer",
            arguments={"summary": "S", "chart_ref": "", "confidence": "high", "reasoning": "r"},
            tool_call_id="call_END",
        )
    ]

    list(run_agent_loop("Q", dummy_df, api_key="dummy_key"))
    
    # Check the messages list passed to call_llm on the SECOND call
    # It should contain: system, user, assistant (tool_call), tool (observation)
    assert mock_call_llm.call_count == 2
    args, kwargs = mock_call_llm.call_args_list[1]
    history = args[0]
    
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[2]["role"] == "assistant"
    assert history[3]["role"] == "tool"
    
    # Threading check
    assert history[2]["tool_calls"][0]["id"] == "call_MATCH"
    assert history[3]["tool_call_id"] == "call_MATCH"


@patch("backend.agent.loop.call_llm")
def test_invalid_final_answer_confidence_continues_loop(mock_call_llm: MagicMock, dummy_df: pd.DataFrame) -> None:
    """If final_answer has an invalid confidence, it does NOT end the loop, it yields an observation."""
    mock_call_llm.side_effect = [
        LLMTurn(
            tool_name="final_answer",
            arguments={"summary": "S", "chart_ref": "", "confidence": "INVALID", "reasoning": "r"},
            tool_call_id="call_1",
        ),
        LLMTurn(
            tool_name="final_answer",
            arguments={"summary": "S", "chart_ref": "", "confidence": "medium", "reasoning": "r"},
            tool_call_id="call_2",
        ),
    ]

    events = list(run_agent_loop("Q", dummy_df, api_key="dummy_key"))
    types = [e["type"] for e in events]
    
    assert types == [
        "stream_start",
        "tool_call",     # invalid confidence
        "observation",   # error returned to LLM
        "tool_call",     # retry
        "final_answer",  # success
        "stream_end",
    ]
