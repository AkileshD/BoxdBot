<!-- ============================================================
  STOP — READ THIS FIRST
  No UI code should be written based on this file alone.
  The workflow defined in SPEC.md (§0, design/ section) is:
    1. These written requirements (this file) ✅
    2. User sketches → placed in design/mock/
    3. Agent reviews the mock
    4. User approves the mock
    5. Only then does any UI implementation begin.
  If design/mock/ is empty, no UI work proceeds.
  ============================================================ -->

# BoxdBot — UI Requirements

**Status:** Requirements written. Awaiting user sketches in `design/mock/` before any UI implementation begins.

**Source of truth for decisions:** SPEC.md. This file translates the relevant spec sections into concrete UI requirements — it does not override the spec.

---

## 1. Overview

The BoxdBot UI is a single-page, local-only web application (React). It has four primary areas that must all be present and functional in v1:

1. **Key & CSV Upload interface** — entry point, first thing a user sees.
2. **Chat input** — how the user asks questions.
3. **Live reasoning trace panel** — shows the agent's turn-by-turn thinking as it happens.
4. **Chart display area** — shows the chart produced by the agent's `make_chart` call.

---

## 2. Key & CSV Upload Interface

**What it is:** Before any questions can be asked, the user must provide two things: their Groq API key and their Letterboxd CSV export file.

**Requirements:**
- A text input (masked/password type) for the Groq API key.
- A file picker for the CSV upload.
- A clear "Submit / Start session" action.
- Visible confirmation once both are accepted (e.g. filename shown, key accepted indicator).
- The key must never be persisted to disk or sent anywhere other than the Groq API. It is held in memory/session only (SPEC.md §7).
- If either is missing, the rest of the UI should be disabled/locked.

**UX note:** This is a setup step, not a recurring action. It can be a modal, a top-of-page form, or a dedicated "setup" screen — to be determined by the approved mock.

---

## 3. Chat Input

**What it is:** The user types a natural-language question about their Letterboxd data here.

**Requirements:**
- A text input or textarea for the question.
- A submit action (button and/or Enter key).
- Should be disabled while the agent is actively running (prevents mid-run re-submission).
- Should re-enable once a `final_answer` has been received.
- May optionally show the history of previous questions asked in the session.

**UX note:** The exact layout (inline input, bottom-bar style, sidebar, etc.) is to be determined by the approved mock.

---

## 4. Live Reasoning Trace Panel

**What it is:** The central differentiator of BoxdBot. Shows the agent's step-by-step reasoning *as it happens*, not just the final answer. Each turn in the agent loop produces a visible entry here.

**Requirements:**
- Must update live during a run, not only after the agent finishes (SPEC.md §3, §6). This requires SSE or polling from the backend — SSE preferred (SPEC.md §7).
- Each entry in the trace should distinguish between, at minimum:
  - **Tool call:** which tool the agent chose to invoke and with what arguments.
  - **Observation:** the result returned by the tool (e.g. a data summary, an error message).
- The panel should scroll automatically as new entries appear.
- Errors returned from tools (e.g. bad pandas code) should be visible here as observations — they are part of the self-correction story (SPEC.md §4).
- The clarifying-question action (`ask_clarification`) and thinness flag (`flag_thin_finding`) should also appear here as trace entries.

**UX note:** The visual treatment (collapsible steps, colour coding, monospace vs. prose, etc.) is to be determined by the approved mock. The requirements here are structural.

---

## 5. Chart Display Area

**What it is:** The visual output of the agent's analysis. Rendered after the agent calls `make_chart` and a `final_answer` is returned.

**Requirements:**
- Displays the chart produced by the backend's `make_chart` tool (SPEC.md §4).
- If the backend uses Plotly: rendered as an interactive Plotly chart via `react-plotly.js` (SPEC.md §7).
- If the backend uses Matplotlib: displayed as a served image.
- The final written insight from `final_answer.summary` should appear alongside or adjacent to the chart.
- If `flag_thin_finding` was called during the run, a clear caveat/warning should appear with the result (not buried in the trace).
- If the agent produced no chart for a given question (edge case), this area should handle that gracefully (no broken placeholder).

**UX note:** Positioning relative to the trace panel (side-by-side, below, tabbed, etc.) is to be determined by the approved mock.

---

## 6. General / Cross-Cutting Requirements

- **Single page:** All four areas coexist on one page or screen (no multi-page routing needed for v1).
- **Local only:** No login, no accounts, no network calls other than to the Groq API.
- **Responsive enough:** Should be usable at a typical laptop screen width. Mobile optimisation is not a v1 requirement.
- **Error states:** Network errors, API errors, and bad-CSV errors should surface clearly in the UI — not silently fail.
- **Session scope:** All state (uploaded CSV, running trace, current chart) is session-scoped. A page refresh resets everything (SPEC.md §5, §6 — session boundary decision pending).

---

## 7. What This File Does Not Specify

- Visual design (colours, typography, layout, spacing) — determined by mock.
- Exact component structure or file organisation — implementation detail.
- Anything about backend endpoints — see SPEC.md §7 and the relevant BUILDING.md session once that is built.

---

*Next step: user produces sketches and places them in `design/mock/`. No UI code is written before that.*
