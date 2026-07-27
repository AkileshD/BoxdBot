"""
LLM Client Wrapper (SPEC.md §3c).

Isolates all OpenAI/Groq SDK complexity. The loop only sees plain Python types
and the LLMTurn dataclass.
"""

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class LLMTurn:
    """A single tool-call chosen by the LLM."""
    tool_name: str
    arguments: dict[str, Any]
    tool_call_id: str


def call_llm(messages: list[dict[str, Any]], tools: list[dict[str, Any]], api_key: str) -> LLMTurn:
    """
    Call the LLM with the current message history and available tools.

    Parameters
    ----------
    messages:
        The conversation history (role/content dicts).
    tools:
        The JSON schemas of the available tools.

    Returns
    -------
    LLMTurn containing the chosen tool's name, parsed arguments, and call ID.

    Raises
    ------
    ValueError
        If the LLM returns no tool calls, or if the arguments are invalid JSON.
    openai.OpenAIError
        On any network or API-level failure (rate limit, etc.). Not caught here;
        the loop is responsible for handling it.
    """
    # Instantiate client per-call with the BYO key passed from the frontend.
    # Groq's OpenAI-compatible endpoint is used.
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    response = client.chat.completions.create(
        # Standard model for the agent — we can make this configurable later,
        # but hardcoding llama3 for v1 is fine.
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.0,
    )

    message = response.choices[0].message
    if not message.tool_calls:
        raise ValueError("LLM returned a text response instead of a tool call.")

    # We only handle the first tool call (single-action ReAct loop).
    tool_call = message.tool_calls[0]
    
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned malformed JSON arguments: {exc}") from exc

    return LLMTurn(
        tool_name=tool_call.function.name,
        arguments=arguments,
        tool_call_id=tool_call.id,
    )
