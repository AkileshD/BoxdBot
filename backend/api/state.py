"""
Server-side State Model (SPEC.md §1).

This is a local, single-user tool. As such, state is stored in simple module-level
globals rather than UUID-keyed multi-tenant session dicts (Decision G).
Multi-tenant/multi-tab session management is an explicit non-goal.
"""

from typing import Any
import pandas as pd

from backend.memory.db import Finding

# The active dataset for the current session.
# Loaded via POST /api/session/new (CSV upload).
current_df: pd.DataFrame | None = None

# The history of findings read from the database when the session started.
# Used to populate the agent's context.
past_findings: list[Finding] = []
