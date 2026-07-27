"""
Agent Loop (SPEC.md §3, §3a, §4).

Implements the while loop that calls the LLM, dispatches tools, appends observations,
and enforces the max-turn cap.
Yields structured event dicts matching the SSE payload shapes (§7a) so the FastAPI
layer (when built) can just stream them directly.
"""

import json
import traceback
from typing import Any, Generator

import pandas as pd

from backend.agent.llm_client import call_llm
from backend.tools.control_actions import (
    ask_clarification,
    final_answer,
    flag_thin_finding,
)
from backend.tools.make_chart import make_chart
from backend.tools.run_pandas import run_pandas

# ── Tool Schemas (§3a, §4) ─────────────────────────────────────────────────────

# Reasoning is required on every tool per §3a.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_pandas",
            "description": "Run pandas/numpy code against the session dataframe to analyze data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code. Must assign its output to a variable named `result`.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief plain-English explanation of why you are running this code.",
                    },
                },
                "required": ["code", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_chart",
            "description": "Create a chart from data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": ["string", "number"]},
                                "value": {"type": "number"},
                            },
                            "required": ["label", "value"],
                        },
                        "description": "List of data points to plot.",
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "scatter"],
                        "description": "Type of chart to draw.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why you are making this chart.",
                    },
                },
                "required": ["data", "chart_type", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Pause and ask the user a clarifying question if their intent is ambiguous.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the user.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why clarification is needed.",
                    },
                },
                "required": ["question", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flag_thin_finding",
            "description": "Attach a caveat when a finding is based on a very small sample size.",
            "parameters": {
                "type": "object",
                "properties": {
                    "finding": {
                        "type": "string",
                        "description": "The finding being flagged.",
                    },
                    "sample_size": {
                        "type": "integer",
                        "description": "The number of data points the finding is based on.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this finding is considered thin.",
                    },
                },
                "required": ["finding", "sample_size", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Deliver the final answer to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Short written insight answering the user's question.",
                    },
                    "chart_ref": {
                        "type": "string",
                        "description": "The chart_id returned by make_chart, or empty string if no chart.",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Self-assessed confidence in the finding.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this is the final answer.",
                    },
                },
                "required": ["summary", "chart_ref", "confidence", "reasoning"],
            },
        },
    },
]


# ── Core Loop ──────────────────────────────────────────────────────────────────

def run_agent_loop(
    question: str,
    df: pd.DataFrame,
    api_key: str,
    max_turns: int = 10,  # §3 Decision C
) -> Generator[dict[str, Any], None, None]:
    """
    Executes the ReAct loop for a single user question.
    Yields event dicts mapping to §7a SSE payloads.
    """
    schema_str = ", ".join([f"'{col}': {dtype}" for col, dtype in df.dtypes.items()])
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are BoxdBot, an expert data analyst for a user's personal movie-watching diary. "
                "Write code to answer their question, make a chart if helpful, and return a final answer. "
                "If a finding is based on a tiny sample, flag it as thin before giving your final answer.\n\n"
                f"DATA SCHEMA: The dataframe has the following columns and types: {schema_str}\n\n"
                "ENVIRONMENT RULES: You are writing code for a sandboxed environment where `pandas` and `numpy` "
                "are already injected. You must **not** use `import` statements. The data is already loaded as a pandas DataFrame named `df`.\n\n"
                "TOOL DISCIPLINE: Only use `ask_clarification` if the user's request is fundamentally impossible "
                "to interpret. You are strictly forbidden from using it as a fallback when your `run_pandas` code fails. "
                "If your code returns an error, read the error, rewrite your code, and try again."
            )
        },
        {"role": "user", "content": question},
    ]

    yield {"type": "stream_start", "question": question}

    turn_index = 0
    while turn_index < max_turns:
        turn_index += 1

        # 1. Call LLM
        try:
            turn = call_llm(messages, TOOLS, api_key)
        except Exception as exc:
            yield {"type": "error", "message": f"LLM Call Failed: {exc}"}
            yield {"type": "stream_end"}
            return

        # Append the assistant's tool-call intent to history
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": turn.tool_call_id,
                "type": "function",
                "function": {
                    "name": turn.tool_name,
                    "arguments": json.dumps(turn.arguments),
                }
            }]
        })

        reasoning = turn.arguments.get("reasoning", "")

        yield {
            "type": "tool_call",
            "turn_index": turn_index,
            "tool_name": turn.tool_name,
            "args": turn.arguments,
            "reasoning": reasoning,
        }

        # 2. Dispatch Tool
        try:
            if turn.tool_name == "run_pandas":
                code = turn.arguments.get("code", "")
                result = run_pandas(code=code, reasoning=reasoning, df=df)

            elif turn.tool_name == "make_chart":
                data = turn.arguments.get("data", [])
                chart_type = turn.arguments.get("chart_type", "")
                result = make_chart(data=data, chart_type=chart_type, reasoning=reasoning)

            elif turn.tool_name == "ask_clarification":
                q = turn.arguments.get("question", "")
                result = ask_clarification(question=q, reasoning=reasoning)

            elif turn.tool_name == "flag_thin_finding":
                finding = turn.arguments.get("finding", "")
                sample_size = turn.arguments.get("sample_size", 0)
                result = flag_thin_finding(finding=finding, sample_size=sample_size, reasoning=reasoning)

            elif turn.tool_name == "final_answer":
                summary = turn.arguments.get("summary", "")
                chart_ref = turn.arguments.get("chart_ref", "")
                confidence = turn.arguments.get("confidence", "")
                result = final_answer(summary=summary, chart_ref=chart_ref, confidence=confidence, reasoning=reasoning)

            else:
                result = {"error": f"Unknown tool: {turn.tool_name}"}

        except Exception as exc:
            # Catch-all for unexpected tool crashes (though tools are designed not to raise)
            result = {"error": f"Tool crashed unexpectedly: {traceback.format_exc()}"}

        # 3. Handle Control Flow & Append Observation
        messages.append({
            "role": "tool",
            "tool_call_id": turn.tool_call_id,
            "name": turn.tool_name,
            "content": json.dumps(result),
        })

        action = result.get("action")
        
        if action == "ask_clarification":
            yield {
                "type": "clarification",
                "turn_index": turn_index,
                "question": result.get("question", ""),
            }
            yield {"type": "stream_end"}
            return

        elif action == "final_answer":
            if result.get("error"):
                # Invalid confidence — don't end loop, just yield observation and continue so LLM can retry
                yield {
                    "type": "observation",
                    "turn_index": turn_index,
                    "tool_name": turn.tool_name,
                    "result": result,
                }
                continue
                
            yield {
                "type": "final_answer",
                "summary": result.get("summary", ""),
                "chart_ref": result.get("chart_ref", ""),
                "confidence": result.get("confidence", ""),
            }
            yield {"type": "stream_end"}
            return

        elif action == "flag_thin_finding":
            yield {
                "type": "thin_flag",
                "turn_index": turn_index,
                "finding": result.get("finding", ""),
                "sample_size": result.get("sample_size", 0),
            }
            # Note: loop continues after flagging thin finding per §4
            yield {
                "type": "observation",
                "turn_index": turn_index,
                "tool_name": turn.tool_name,
                "result": result,
            }
        
        else:
            # Standard observation (run_pandas, make_chart, or tool error)
            yield {
                "type": "observation",
                "turn_index": turn_index,
                "tool_name": turn.tool_name,
                "result": result,
            }

    # 4. Max-turn cap hit
    yield {
        "type": "error", 
        "message": f"Agent loop aborted: max turns ({max_turns}) exceeded without reaching a final answer."
    }
    yield {"type": "stream_end"}
