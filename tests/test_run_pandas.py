"""
Tests for backend/tools/run_pandas.py (SPEC.md §4, §4a, §3a).

Test categories:
  - Normal successful operations
  - Sandbox security: import attempt, file-open attempt
  - Timeout: infinite loop
  - Error handling: bad code, missing result variable
  - reasoning field contract: present in signature, not used by sandbox

The dataframe used throughout is a small synthetic fixture.
THIS IS A TEMPORARY TEST FIXTURE — not the real data-loading path.
Real CSV loading (user uploads Letterboxd export → pandas reads it → held
in session state) is a separate, later component. This df exists only so
run_pandas can be tested in isolation.
"""

import time

import pandas as pd
import pytest

from backend.tools.run_pandas import RunResult, _SAFE_BUILTINS, run_pandas


# ── Synthetic test dataframe (TEMPORARY FIXTURE — not the real data path) ─────

@pytest.fixture()
def df() -> pd.DataFrame:
    """
    Minimal Letterboxd-shaped dataframe for isolated tool testing.
    Not the real data-loading path — see module docstring.
    """
    return pd.DataFrame({
        "Film": ["Mulholland Drive", "Parasite", "Yi Yi", "Jeanne Dielman", "Chungking Express"],
        "Rating": [5.0, 4.5, 5.0, 4.0, 4.5],
        "Year": [2001, 2019, 2000, 1975, 1994],
        "Genre": ["Mystery", "Thriller", "Drama", "Drama", "Romance"],
        "Watched Date": ["2024-01-10", "2024-02-14", "2024-03-01", "2024-03-15", "2024-04-05"],
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

REASONING = "Running a basic analysis to answer the question."


# ── Normal successful operations ──────────────────────────────────────────────

def test_basic_count(df: pd.DataFrame) -> None:
    """Agent asks how many films are in the dataset."""
    res = run_pandas("result = len(df)", REASONING, df)
    assert res["status"] == "ok"
    assert res["result"] == "5"
    assert res["error"] is None


def test_mean_rating(df: pd.DataFrame) -> None:
    """Agent computes mean rating."""
    res = run_pandas("result = df['Rating'].mean()", REASONING, df)
    assert res["status"] == "ok"
    assert float(res["result"]) == pytest.approx(4.6)


def test_groupby(df: pd.DataFrame) -> None:
    """Agent groups by Genre and counts."""
    code = "result = df.groupby('Genre')['Film'].count().to_dict()"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "ok"
    import ast
    counts = ast.literal_eval(res["result"])
    assert counts["Drama"] == 2


def test_stdout_captured(df: pd.DataFrame) -> None:
    """Print output from agent code is captured in stdout field."""
    code = "print('hello from agent'); result = 42"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "ok"
    assert "hello from agent" in res["stdout"]
    assert res["result"] == "42"


def test_missing_result_variable(df: pd.DataFrame) -> None:
    """Code that runs but forgets to assign result gets a helpful message."""
    code = "x = df['Rating'].mean()  # forgot to assign to result"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "ok"
    assert res["result"] is None
    assert "result" in res["error"]   # error message mentions the variable name


# ── §3a: reasoning field ──────────────────────────────────────────────────────

def test_reasoning_field_accepted(df: pd.DataFrame) -> None:
    """
    reasoning is a required arg in the signature (§3a tool schema contract).
    The sandbox itself does not use it — this test confirms it is accepted
    without affecting execution.
    """
    res = run_pandas(
        "result = 1 + 1",
        reasoning="I need to verify basic arithmetic works.",
        df=df,
    )
    assert res["status"] == "ok"
    assert res["result"] == "2"


# ── Sandbox security tests ────────────────────────────────────────────────────

def test_import_os_blocked(df: pd.DataFrame) -> None:
    """
    Attempt to import os — should fail. __import__ is not in _SAFE_BUILTINS
    and the `import` statement relies on __import__ internally.
    """
    code = "import os; result = os.getcwd()"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error", f"Expected error, got: {res}"
    # The error message should indicate import is blocked
    assert res["result"] is None


def test_import_via_dunder_blocked(df: pd.DataFrame) -> None:
    """
    Attempt to use __import__ directly — should be absent from builtins.
    """
    code = "result = __import__('os').getcwd()"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error", f"Expected error, got: {res}"
    assert res["result"] is None


def test_open_file_blocked(df: pd.DataFrame) -> None:
    """
    Attempt to open a file — `open` is not in _SAFE_BUILTINS.
    """
    code = "result = open('/etc/passwd').read()"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error", f"Expected error, got: {res}"
    assert res["result"] is None


def test_builtins_escalation_blocked(df: pd.DataFrame) -> None:
    """
    Attempt to reach the real builtins module via __builtins__ and use it
    to get __import__. Our __builtins__ is a plain dict, not the module,
    so dict["__import__"] will raise KeyError and subsequent import will fail.
    """
    code = "b = __builtins__; result = b['__import__']('os').getcwd()"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error", f"Expected error, got: {res}"


def test_sys_not_reachable(df: pd.DataFrame) -> None:
    """sys is not in globals — accessing it directly should raise NameError."""
    code = "result = sys.version"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error"
    assert "sys" in res["error"]


def test_exec_not_in_builtins(df: pd.DataFrame) -> None:
    """exec is not in _SAFE_BUILTINS — calling it should raise NameError."""
    code = "exec('import os'); result = 'escaped'"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error"
    assert res["result"] is None


# ── Timeout test ──────────────────────────────────────────────────────────────

def test_infinite_loop_times_out(df: pd.DataFrame) -> None:
    """
    An infinite loop must be caught by the thread join timeout and returned
    as a timeout observation — never hang the test suite or harness.
    Uses a very short timeout (1 s) so the test completes quickly.
    """
    code = "while True: pass"
    start = time.monotonic()
    res = run_pandas(code, REASONING, df, timeout=1.0)
    elapsed = time.monotonic() - start

    assert res["status"] == "timeout", f"Expected timeout, got: {res}"
    assert res["result"] is None
    assert "timed out" in res["error"].lower()
    # Should return in roughly 1 second, not hang
    assert elapsed < 5.0, f"Timed out test took too long: {elapsed:.1f}s"


# ── Error handling: bad code ──────────────────────────────────────────────────

def test_syntax_error_returned(df: pd.DataFrame) -> None:
    """SyntaxError in agent code is caught and returned, not raised to harness."""
    code = "result = df['Rating'].mean("  # unclosed paren
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error"
    assert res["error"] is not None
    assert res["result"] is None


def test_key_error_returned(df: pd.DataFrame) -> None:
    """Accessing a nonexistent column returns an error observation."""
    code = "result = df['NonexistentColumn'].mean()"
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "error"
    assert "KeyError" in res["error"] or "NonexistentColumn" in res["error"]


# ── _SAFE_BUILTINS whitelist integrity check ──────────────────────────────────

def test_safe_builtins_does_not_contain_dangerous_names() -> None:
    """
    Direct inspection of _SAFE_BUILTINS — confirm dangerous names are absent.
    This is a structural test: if someone edits the whitelist accidentally,
    this catches it before it reaches code review.
    """
    forbidden = [
        "__import__", "open", "eval", "exec", "compile",
        "breakpoint", "input", "vars", "dir",
        "globals", "locals", "getattr", "setattr", "delattr",
    ]
    for name in forbidden:
        assert name not in _SAFE_BUILTINS, (
            f"Dangerous builtin '{name}' found in _SAFE_BUILTINS — remove it."
        )


# ── Defensive copy per call (§4a-ii) ─────────────────────────────────────────

def test_inplace_mutation_does_not_affect_original(df: pd.DataFrame) -> None:
    """
    Agent code that mutates df inplace must not change the caller's dataframe.
    Proves the df.copy() in run_pandas() isolates each call (§4a-ii).
    """
    original_columns = list(df.columns)
    original_len = len(df)

    # Call 1: agent drops a column inplace and modifies values
    code = (
        "df.drop(columns=['Genre'], inplace=True)\n"
        "df['Rating'] = 0.0\n"
        "result = list(df.columns)"
    )
    res = run_pandas(code, REASONING, df)
    assert res["status"] == "ok"
    # The sandbox saw the mutation — 'Genre' gone inside the sandbox
    assert "Genre" not in res["result"]

    # Caller's df is unchanged
    assert list(df.columns) == original_columns, (
        "Caller's df.columns changed — defensive copy is not working."
    )
    assert len(df) == original_len, (
        "Caller's df length changed — defensive copy is not working."
    )
    # Caller's Rating column is unchanged (not zeroed out)
    assert df["Rating"].tolist() == [5.0, 4.5, 5.0, 4.0, 4.5], (
        "Caller's df values changed — defensive copy is not working."
    )


def test_mutation_does_not_leak_between_calls(df: pd.DataFrame) -> None:
    """
    A column dropped in call N must still be present in call N+1.
    Proves isolation across sequential calls in the same session (§4a-ii).
    """
    # Call 1: drops 'Year'
    res1 = run_pandas(
        "df.drop(columns=['Year'], inplace=True); result = list(df.columns)",
        REASONING,
        df,
    )
    assert res1["status"] == "ok"
    assert "Year" not in res1["result"]

    # Call 2: 'Year' must still be accessible
    res2 = run_pandas(
        "result = df['Year'].tolist()",
        REASONING,
        df,
    )
    assert res2["status"] == "ok", (
        f"'Year' column missing in call 2 — mutation leaked across calls.\n{res2}"
    )
    assert "2001" in res2["result"]  # first entry year

