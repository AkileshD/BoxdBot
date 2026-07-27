"""
Tests for backend/agent/llm_client.py (SPEC.md §3c).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.agent.llm_client import LLMTurn, call_llm


def _make_mock_response(tool_name: str, arguments: dict, tool_call_id: str) -> MagicMock:
    """Helper to build a mocked OpenAI chat completion response."""
    # Build the deeply nested mock structure expected by call_llm
    tool_call = MagicMock()
    tool_call.id = tool_call_id
    tool_call.function.name = tool_name
    tool_call.function.arguments = json.dumps(arguments)

    message = MagicMock()
    message.tool_calls = [tool_call]

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    
    return response


def _make_mock_text_response() -> MagicMock:
    """Helper for when the LLM returns plain text instead of a tool call."""
    message = MagicMock()
    message.tool_calls = None
    
    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    
    return response


@patch("backend.agent.llm_client.OpenAI")
def test_call_llm_parses_tool_call_correctly(mock_openai_class: MagicMock) -> None:
    # Setup mock client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Setup mock response
    mock_response = _make_mock_response(
        tool_name="run_pandas",
        arguments={"code": "df.head()", "reasoning": "checking data"},
        tool_call_id="call_123",
    )
    mock_client.chat.completions.create.return_value = mock_response

    # Execute
    turn = call_llm(messages=[], tools=[], api_key="dummy_key")

    # Assert correct unpack into LLMTurn dataclass
    assert isinstance(turn, LLMTurn)
    assert turn.tool_name == "run_pandas"
    assert turn.arguments == {"code": "df.head()", "reasoning": "checking data"}
    assert turn.tool_call_id == "call_123"

    # Verify client was called with correct parameters
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["tool_choice"] == "auto"


@patch("backend.agent.llm_client.OpenAI")
def test_call_llm_raises_on_text_response(mock_openai_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_response = _make_mock_text_response()
    mock_client.chat.completions.create.return_value = mock_response

    with pytest.raises(ValueError, match="returned a text response instead of a tool call"):
        call_llm(messages=[], tools=[], api_key="dummy_key")


@patch("backend.agent.llm_client.OpenAI")
def test_call_llm_raises_on_malformed_json_args(mock_openai_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Build a mock response where the arguments string is invalid JSON
    tool_call = MagicMock()
    tool_call.function.arguments = "{broken_json:"
    message = MagicMock()
    message.tool_calls = [tool_call]
    choice = MagicMock()
    choice.message = message
    mock_response = MagicMock()
    mock_response.choices = [choice]
    
    mock_client.chat.completions.create.return_value = mock_response

    with pytest.raises(ValueError, match="malformed JSON arguments"):
        call_llm(messages=[], tools=[], api_key="dummy_key")
