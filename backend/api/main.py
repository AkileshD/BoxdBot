"""
FastAPI Server (SPEC.md §7a, §3b).

Exposes the session boundary endpoints and the SSE chat endpoint.
"""

import os
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agent.loop import run_agent_loop
from backend.api import state
from backend.memory.db import ToolCallRecord, append_one, read_all

app = FastAPI(title="BoxdBot API")

# Allow local frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_db_path() -> str:
    return os.environ.get("FINDINGS_DB_PATH", "findings_log.db")


# ── Session Boundary (§3b) ─────────────────────────────────────────────────────

@app.post("/api/session/new")
async def create_session(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """
    Start a new session (Decision E).
    Atomic upload of the CSV data. Loads it into the global current_df.
    Reads past findings from SQLite and loads them into global past_findings.
    Returns the past findings to the frontend.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Load CSV into pandas dataframe
        df = pd.read_csv(file.file)
        
        # Clean column names (standard pandas hygiene)
        df.columns = df.columns.str.strip()
        
        state.current_df = df
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {exc}") from exc

    # Load past findings from the database
    try:
        past_findings = read_all(_get_db_path())
        state.past_findings = past_findings
    except Exception as exc:
        # If DB doesn't exist yet, that's fine. If it's a real error, surface it.
        raise HTTPException(status_code=500, detail=f"Failed to read findings log: {exc}") from exc

    return {
        "status": "ok",
        "past_findings": past_findings,
    }


class EndSessionRequest(BaseModel):
    question: str
    summary: str
    confidence: str
    chart_ref: str = ""
    tool_calls_used: list[ToolCallRecord] = []


@app.post("/api/session/end")
def end_session(request: EndSessionRequest) -> dict[str, str]:
    """
    End the current session (§3b).
    Appends the provided finding to the SQLite log and clears the active dataframe.
    """
    try:
        append_one(
            db_path=_get_db_path(),
            question=request.question,
            finding_summary=request.summary,
            confidence=request.confidence,
            chart_ref=request.chart_ref,
            tool_calls_used=request.tool_calls_used,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write finding to log: {exc}") from exc

    # Clear state
    state.current_df = None
    state.past_findings = []

    return {"status": "ok"}


# ── Chat / Agent Loop (§7a) ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    api_key: str  # BYO key passed per request (Decision F)


@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """
    Stream the agent loop's reasoning trace and final answer via SSE.
    Requires a session to have been started (current_df must not be None).
    """
    if state.current_df is None:
        raise HTTPException(status_code=400, detail="No active session. Please start a new session with a CSV file.")

    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="API key is required.")

    # Convert the generator's yielded dicts into SSE formatted messages
    def event_publisher():
        # run_agent_loop yields dicts that perfectly map to SSE payloads.
        generator = run_agent_loop(
            question=request.question,
            df=state.current_df,
            api_key=request.api_key.strip(),
        )
        
        for event_dict in generator:
            event_type = event_dict.pop("type")
            
            # sse-starlette expects a dict with 'event' (type) and 'data' (JSON payload string)
            yield {
                "event": event_type,
                "data": json.dumps(event_dict) if event_dict else "{}",
            }

    import json
    return EventSourceResponse(event_publisher())
