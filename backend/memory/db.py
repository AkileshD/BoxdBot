"""
Episodic findings log — SQLite storage (SPEC.md §5, §5a).

Access pattern per spec:
  - read_all()   : called once at New Session to load prior findings into context.
  - append_one() : called once at End Session to persist the current session's finding.

No indexing, no query filters, no ORM — stdlib sqlite3 only (§5a).

Schema matches SPEC.md §5 exactly:
  timestamp        TEXT   — ISO-8601 string, set by append_one() at call time.
  question         TEXT   — the user's original question for this session.
  finding_summary  TEXT   — the agent's short written insight (from final_answer.summary).
  chart_ref        TEXT   — reference to the chart file/id produced, or empty string.
  confidence       TEXT   — one of: "high" | "medium" | "low" (§4c).
  tool_calls_used  TEXT   — JSON-serialised list of {"tool": str, "args": dict} objects.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


# ── Types ─────────────────────────────────────────────────────────────────────

class ToolCallRecord(TypedDict):
    tool: str
    args: dict


class Finding(TypedDict):
    """One row from the findings table, exactly matching the SPEC.md §5 schema."""
    timestamp: str
    question: str
    finding_summary: str
    chart_ref: str
    confidence: str          # "high" | "medium" | "low"
    tool_calls_used: list[ToolCallRecord]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection and ensure the findings table exists."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row   # rows accessible by column name
    conn.execute("PRAGMA journal_mode=WAL;")  # safer concurrent access
    conn.execute("""
        CREATE TABLE IF NOT EXISTS findings (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT    NOT NULL,
            question         TEXT    NOT NULL,
            finding_summary  TEXT    NOT NULL,
            chart_ref        TEXT    NOT NULL DEFAULT '',
            confidence       TEXT    NOT NULL,
            tool_calls_used  TEXT    NOT NULL DEFAULT '[]'
        );
    """)
    conn.commit()
    return conn


# ── Public API ────────────────────────────────────────────────────────────────

def read_all(db_path: str | Path) -> list[Finding]:
    """
    Read every finding from the log and return them as a list, oldest first.

    Called once at New Session (§3b) to load prior findings into the agent's
    context. Linear scan — no filtering, no indexing (§5a).

    Returns an empty list if the database does not yet exist.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return []

    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT timestamp, question, finding_summary, chart_ref, "
            "       confidence, tool_calls_used "
            "FROM findings ORDER BY id ASC;"
        ).fetchall()
    finally:
        conn.close()

    findings: list[Finding] = []
    for row in rows:
        findings.append(Finding(
            timestamp=row["timestamp"],
            question=row["question"],
            finding_summary=row["finding_summary"],
            chart_ref=row["chart_ref"],
            confidence=row["confidence"],
            tool_calls_used=json.loads(row["tool_calls_used"]),
        ))
    return findings


def append_one(
    db_path: str | Path,
    *,
    question: str,
    finding_summary: str,
    confidence: str,
    chart_ref: str = "",
    tool_calls_used: list[ToolCallRecord] | None = None,
) -> None:
    """
    Append a single finding to the log.

    Called once at End Session (§3b) to persist the current session's result.
    The timestamp is set here to UTC ISO-8601 at the moment of the call.

    Args:
        db_path:          Path to the SQLite file (created if absent).
        question:         The user's original question for this session.
        finding_summary:  The agent's short written insight (final_answer.summary).
        confidence:       One of "high" | "medium" | "low" (§4c).
        chart_ref:        Reference to the chart produced, or "" if none.
        tool_calls_used:  List of {"tool": str, "args": dict} records (§5 schema).
    """
    db_path = Path(db_path)
    tool_calls_used = tool_calls_used or []

    conn = _connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO findings
                (timestamp, question, finding_summary, chart_ref,
                 confidence, tool_calls_used)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                question,
                finding_summary,
                chart_ref,
                confidence,
                json.dumps(tool_calls_used),
            ),
        )
        conn.commit()
    finally:
        conn.close()
