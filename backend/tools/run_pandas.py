"""
run_pandas tool — sandboxed code execution (SPEC.md §4, §4a, §3a).

Public surface
--------------
run_pandas(code, reasoning, df, timeout) -> RunResult

The `reasoning` parameter is part of the tool schema/args contract per §3a —
every tool call must include a reasoning field populated by the LLM. The
sandbox itself does not use `reasoning`; the harness reads it from the call
args and forwards it in the SSE tool_call event (§7a). It is accepted here
as a required argument so the function signature matches the tool schema
exactly, making the contract explicit and testable.

Restricted globals
------------------
exec() receives a custom globals dict containing:
  - "pd" / "pandas": the pandas module
  - "np" / "numpy":  the numpy module
  - "df":            the session dataframe (read-only by convention; exec
                     cannot enforce immutability, but the agent has no path
                     to persist mutations across calls)
  - "__builtins__":  a minimal whitelist of safe builtins (see _SAFE_BUILTINS)

Critically absent from the globals / __builtins__:
  __import__, open, eval, exec, compile, breakpoint, input,
  vars, dir, globals, locals, getattr, setattr, delattr,
  os, sys, socket, subprocess — and the full builtins module.

Timeout (§4a, §4a-i)
-------------
Code runs on a daemon thread. thread.join(timeout=N) is called. If the
thread is still alive after N seconds, execution is declared failed and a
timeout observation is returned to the agent. The thread is marked daemon so
it does not prevent process exit.

APPROVED DEFAULT: N = 10 seconds (§4a-i). The value is passed as an argument
so the harness can override it without modifying this module.

Result capture
--------------
The executed code is expected to assign a variable named `result`. The
sandbox reads `result` from the local namespace after execution. If the code
does not assign `result`, a clear message is returned telling the agent what
to fix. stdout/stderr produced by the code is captured and included in the
observation so the agent can see any print() calls.
"""

import io
import sys
import threading
import traceback
from contextlib import redirect_stdout
from typing import TypedDict

import numpy as np
import pandas as pd


# ── Safe builtins whitelist ────────────────────────────────────────────────────
# Exactly the set that is accessible to agent-generated code inside exec().
# Nothing beyond this list can be reached via __builtins__.

_SAFE_BUILTINS: dict = {
    # Numeric / iteration — needed by normal pandas expressions
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sum": sum,
    "sorted": sorted,
    "reversed": reversed,
    # Type constructors
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    # Introspection (safe subset)
    "isinstance": isinstance,
    "issubclass": issubclass,
    "type": type,
    # I/O — print only; useful for agent debugging, output is captured
    "print": print,
    # Exception base (needed for bare `raise` and `except Exception`)
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    # Iteration helpers
    "map": map,
    "filter": filter,
    "any": any,
    "all": all,
    # Deliberately ABSENT (not exhaustive — anything not listed is unreachable):
    # __import__, open, eval, exec, compile, breakpoint, input,
    # vars, dir, globals, locals, getattr, setattr, delattr,
    # __builtins__ (as a module — replaced with this dict),
    # os, sys, socket, subprocess, pathlib, shutil, importlib
}

# KNOWN ACCEPTED GAP (§4a threat model): object-introspection escape chains
# (e.g. ().__class__.__mro__[-1].__subclasses__() to reach file/socket types)
# are not blocked by this whitelist. Blocking them fully requires either a
# restricted AST walker or a subprocess sandbox — both out of scope for a
# local single-user tool per §4a's explicit minimal-threat-model decision.


# ── Result type ────────────────────────────────────────────────────────────────

class RunResult(TypedDict):
    """
    Structured observation returned to the agent after run_pandas executes.

    Fields:
      status:  "ok" | "error" | "timeout"
      result:  Stringified value of the `result` variable set by the code,
               or None if not set (status="ok") / not applicable (error/timeout).
      stdout:  Any text printed by the code (captured from stdout).
      error:   Exception message + traceback (status="error"), timeout message
               (status="timeout"), or None (status="ok").
    """
    status: str    # "ok" | "error" | "timeout"
    result: str | None
    stdout: str
    error: str | None


# ── Internal: thread worker ────────────────────────────────────────────────────

def _exec_worker(
    code: str,
    restricted_globals: dict,
    local_ns: dict,
    stdout_buf: io.StringIO,
    out: list,      # out[0] = RunResult or exception from inside the thread
) -> None:
    """
    Runs inside the daemon thread. Writes a RunResult into out[0].
    Never raises — all exceptions are caught and returned as an error result.
    """
    try:
        with redirect_stdout(stdout_buf):
            exec(code, restricted_globals, local_ns)  # noqa: S102

        captured_stdout = stdout_buf.getvalue()
        raw_result = local_ns.get("result", None)

        if raw_result is None:
            out[0] = RunResult(
                status="ok",
                result=None,
                stdout=captured_stdout,
                error=(
                    "Code executed without error but did not assign a `result` variable. "
                    "Assign the value you want to return to `result = ...`."
                ),
            )
        else:
            out[0] = RunResult(
                status="ok",
                result=str(raw_result),
                stdout=captured_stdout,
                error=None,
            )

    except Exception:  # noqa: BLE001
        out[0] = RunResult(
            status="error",
            result=None,
            stdout=stdout_buf.getvalue(),
            error=traceback.format_exc(),
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def run_pandas(
    code: str,
    reasoning: str,
    df: pd.DataFrame,
    timeout: float = 10.0,
) -> RunResult:
    """
    Execute agent-generated pandas/numpy code in a sandboxed environment.

    Parameters
    ----------
    code:
        The Python code string to execute. Should assign its output to a
        variable named `result`.
    reasoning:
        Required per §3a — the LLM's plain-English explanation of why it is
        calling this tool. Not used by the sandbox; forwarded by the harness
        in the SSE tool_call event. Accepted here so the function signature
        matches the tool schema exactly.
    df:
        The pre-loaded, pre-cleaned session dataframe. A defensive copy
        (`df.copy()`) is made before exec() so agent-generated code cannot
        leak mutations (inplace ops, column drops, index resets) across calls
        or across turns in the same session (§4a-ii).
    timeout:
        Seconds to wait before declaring execution failed. Default: 10 s
        (approved — §4a-i). Passed as an argument so the harness can
        override it without modifying this module.

    Returns
    -------
    RunResult dict with fields: status, result, stdout, error.
    The harness converts this into an observation appended to the message
    history (§3, step 4). Never raises.
    """
    restricted_globals: dict = {
        "__builtins__": _SAFE_BUILTINS,
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "df": df.copy(),   # defensive copy per §4a-ii — isolates each call
    }

    local_ns: dict = {}
    stdout_buf = io.StringIO()
    out: list = [None]   # mutable container so the thread can write into it

    thread = threading.Thread(
        target=_exec_worker,
        args=(code, restricted_globals, local_ns, stdout_buf, out),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Thread still running after timeout — treat as failed.
        # The daemon thread will eventually be cleaned up when the process exits.
        return RunResult(
            status="timeout",
            result=None,
            stdout=stdout_buf.getvalue(),
            error=f"Execution timed out after {timeout} seconds.",
        )

    # Thread finished — out[0] was written by _exec_worker
    return out[0]
