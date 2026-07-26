"""
Smoke tests for backend/memory/db.py.

These tests use a temporary SQLite file (not the real findings_log.db).
Run with:  pytest tests/test_memory.py -v
"""

import json
import tempfile
from pathlib import Path

import pytest

from backend.memory.db import append_one, read_all


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a path inside a temp directory — file does not exist yet."""
    return tmp_path / "test_findings.db"


# ── read_all on a missing file returns [] ─────────────────────────────────────

def test_read_all_missing_file_returns_empty(tmp_db: Path) -> None:
    assert read_all(tmp_db) == []


# ── append then read back ─────────────────────────────────────────────────────

def test_append_one_and_read_back(tmp_db: Path) -> None:
    tool_calls = [
        {"tool": "run_pandas", "args": {"code": "result = df.shape[0]"}},
        {"tool": "final_answer", "args": {"summary": "test", "chart_ref": "", "confidence": "high"}},
    ]

    append_one(
        tmp_db,
        question="How many films did I watch?",
        finding_summary="You watched 42 films.",
        confidence="high",
        chart_ref="chart_001.json",
        tool_calls_used=tool_calls,
    )

    findings = read_all(tmp_db)

    assert len(findings) == 1
    f = findings[0]
    assert f["question"] == "How many films did I watch?"
    assert f["finding_summary"] == "You watched 42 films."
    assert f["confidence"] == "high"
    assert f["chart_ref"] == "chart_001.json"
    assert f["tool_calls_used"] == tool_calls
    # timestamp is an ISO-8601 string
    assert "T" in f["timestamp"]


# ── default optional args ─────────────────────────────────────────────────────

def test_defaults(tmp_db: Path) -> None:
    append_one(
        tmp_db,
        question="What genre do I watch most?",
        finding_summary="Drama.",
        confidence="medium",
    )

    findings = read_all(tmp_db)
    assert len(findings) == 1
    f = findings[0]
    assert f["chart_ref"] == ""
    assert f["tool_calls_used"] == []


# ── multiple appends come back oldest-first ───────────────────────────────────

def test_multiple_appends_order(tmp_db: Path) -> None:
    for i in range(3):
        append_one(
            tmp_db,
            question=f"Question {i}",
            finding_summary=f"Finding {i}",
            confidence="low",
        )

    findings = read_all(tmp_db)
    assert len(findings) == 3
    assert [f["question"] for f in findings] == ["Question 0", "Question 1", "Question 2"]


# ── tool_calls_used round-trips through JSON cleanly ─────────────────────────

def test_tool_calls_json_roundtrip(tmp_db: Path) -> None:
    tool_calls = [{"tool": "run_pandas", "args": {"code": "df.head()"}}]
    append_one(
        tmp_db,
        question="Q",
        finding_summary="S",
        confidence="high",
        tool_calls_used=tool_calls,
    )
    findings = read_all(tmp_db)
    assert findings[0]["tool_calls_used"] == tool_calls
