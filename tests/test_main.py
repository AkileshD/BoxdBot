"""
Tests for backend/api/main.py.

Tests the FastAPI endpoints using TestClient, confirming session state boundary
logic, CSV uploading, SSE formatting, and LLM orchestration.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.agent.llm_client import LLMTurn
from backend.api import state
from backend.api.main import app

client = TestClient(app)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_state():
    """Ensure global state is clean before and after every test."""
    state.current_df = None
    state.past_findings = []
    yield
    state.current_df = None
    state.past_findings = []


@pytest.fixture
def temp_db(tmp_path) -> str:
    """Provides a temporary SQLite path and sets the env var."""
    db_path = str(tmp_path / "test_findings.db")
    os.environ["FINDINGS_DB_PATH"] = db_path
    yield db_path
    # cleanup not strictly necessary as tmp_path is managed by pytest,
    # but we should unset the env var
    os.environ.pop("FINDINGS_DB_PATH", None)


@pytest.fixture
def dummy_csv_content() -> bytes:
    """Minimal Letterboxd-shaped CSV."""
    return b"Date,Name,Year,Letterboxd URI,Rating\n2023-01-01,The Matrix,1999,uri,5.0\n"


# ── /api/session/new ───────────────────────────────────────────────────────────

def test_session_new_uploads_csv_and_sets_state(temp_db: str, dummy_csv_content: bytes):
    response = client.post(
        "/api/session/new",
        files={"file": ("diary.csv", dummy_csv_content, "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["past_findings"] == []
    
    # Verify module-level state was set
    assert state.current_df is not None
    assert len(state.current_df) == 1
    assert state.current_df.iloc[0]["Name"] == "The Matrix"


def test_session_new_returns_past_findings_if_db_exists(temp_db: str, dummy_csv_content: bytes):
    # Seed the DB using the memory module directly
    from backend.memory.db import append_one
    append_one(
        db_path=temp_db,
        question="What is my top film?",
        finding_summary="Matrix",
        confidence="high",
        chart_ref="",
        tool_calls_used=[]
    )

    response = client.post(
        "/api/session/new",
        files={"file": ("diary.csv", dummy_csv_content, "text/csv")},
    )
    
    assert response.status_code == 200
    findings = response.json()["past_findings"]
    assert len(findings) == 1
    assert findings[0]["finding_summary"] == "Matrix"


def test_session_new_rejects_non_csv():
    response = client.post(
        "/api/session/new",
        files={"file": ("diary.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]


# ── /api/session/end ───────────────────────────────────────────────────────────

def test_session_end_appends_to_db_and_clears_state(temp_db: str):
    # Mock active state
    state.current_df = pd.DataFrame()
    state.past_findings = [{"id": "abc"}]

    payload = {
        "question": "Q",
        "summary": "S",
        "confidence": "high",
        "chart_ref": "c1",
        "tool_calls_used": []
    }
    
    response = client.post("/api/session/end", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify state was cleared
    assert state.current_df is None
    assert state.past_findings == []

    # Verify it was written to DB
    from backend.memory.db import read_all
    saved = read_all(temp_db)
    assert len(saved) == 1
    assert saved[0]["question"] == "Q"
    assert saved[0]["finding_summary"] == "S"
    assert saved[0]["confidence"] == "high"


# ── /api/chat ──────────────────────────────────────────────────────────────────

@patch("backend.agent.loop.call_llm")
def test_chat_sse_stream_format(mock_call_llm: MagicMock):
    """Verify SSE streaming format matches §7a requirements."""
    # Setup active session state
    state.current_df = pd.DataFrame({"Rating": [5]})
    
    mock_call_llm.side_effect = [
        LLMTurn(
            tool_name="final_answer",
            arguments={"summary": "It is 5.", "chart_ref": "", "confidence": "high", "reasoning": "done"},
            tool_call_id="call_1",
        )
    ]

    # TestClient can capture streaming responses via `.iter_lines()` or just `.text`
    with client.stream("POST", "/api/chat", json={"question": "Q", "api_key": "dummy_key"}) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Read the raw SSE stream output
        response.read()
        text = response.text
        
    # The stream should look like:
    # event: stream_start
    # data: {"question": "Q"}
    # \n\n
    # event: tool_call
    # ...
    assert "event: stream_start\r\n" in text
    assert "event: tool_call\r\n" in text
    assert "event: final_answer\r\n" in text
    assert "event: stream_end\r\n" in text
    
    # Check JSON data formatting inside one of the events
    # We expect `data: {"turn_index": 1, "tool_name": "final_answer", ...}`
    assert 'data: {"summary": "It is 5."' in text


@patch("backend.agent.loop.call_llm")
def test_chat_passes_api_key_and_forgets_it(mock_call_llm: MagicMock):
    """Verify the API key makes it down to the llm_client but isn't stored."""
    state.current_df = pd.DataFrame()
    
    mock_call_llm.return_value = LLMTurn(
        tool_name="final_answer",
        arguments={"summary": "S", "chart_ref": "", "confidence": "high", "reasoning": "r"},
        tool_call_id="call_1"
    )

    client.post("/api/chat", json={"question": "Q", "api_key": "super_secret_key"})
    
    # Check that call_llm received it
    args, kwargs = mock_call_llm.call_args
    assert kwargs.get("api_key") == "super_secret_key" or args[2] == "super_secret_key"
    
    # Check that it isn't in global state
    assert not hasattr(state, "api_key")


def test_chat_unhappy_path_no_session():
    """/api/chat must 400 if state.current_df is None."""
    state.current_df = None
    response = client.post("/api/chat", json={"question": "Q", "api_key": "key"})
    
    assert response.status_code == 400
    assert "No active session" in response.json()["detail"]


def test_chat_unhappy_path_no_api_key():
    """/api/chat must 400 if api_key is empty/missing."""
    state.current_df = pd.DataFrame()
    
    response = client.post("/api/chat", json={"question": "Q", "api_key": "   "})
    assert response.status_code == 400
    assert "API key is required" in response.json()["detail"]
