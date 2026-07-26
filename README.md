# BoxdBot

A local, single-user LLM-powered agent for analysing your personal [Letterboxd](https://letterboxd.com) data. Upload your Letterboxd diary export (CSV), ask questions in plain English, and get back a short insight and a chart — with the agent's full reasoning trace visible step by step.

> **Status:** Backend in progress. Memory module and `run_pandas` tool complete. Agent loop, FastAPI, and frontend coming next.

---

## What it does

You export your Letterboxd diary, upload it, and ask things like:

- *"What genre do I watch most on weekends?"*
- *"Which director do I rate most consistently?"*
- *"Has my average rating gone up or down over the last year?"*

BoxdBot doesn't do a fixed lookup. An LLM agent plans an approach, writes real pandas analysis code, runs it against your data, checks whether the result actually answers your question, and corrects course if it doesn't. You watch it think turn-by-turn in a live trace panel. The final answer comes with a chart.

Everything runs locally. Your data and your API key never leave your machine.

---

## Architecture highlights

- **Agent loop:** Hybrid ReAct pattern with Groq's native function-calling. No LangChain or agent framework — the loop is a hand-built `while` loop that calls the API, dispatches tools, appends observations, and repeats until `final_answer` or a max-turn cap.
- **Reasoning trace:** Every tool call includes a required `reasoning` field (system-prompt-enforced). The harness forwards it live to the frontend via Server-Sent Events.
- **Sandboxed code execution:** Agent-generated pandas/numpy code runs inside a restricted `exec()` with a custom `__builtins__` whitelist (no `import`, `open`, `eval`, or stdlib access) on a daemon thread with a 10-second join timeout.
- **Episodic memory:** A local SQLite findings log. Read at session start, written at session end. Linear scan — no vector store, no embeddings (not needed at this scale).
- **No hosting:** Runs locally. You supply your own Groq API key and CSV at runtime via the UI.

---

## Stack

| Layer | Technology |
|---|---|
| LLM | Groq API (via `openai` package, OpenAI-compatible endpoint) |
| Data engine | pandas + numpy |
| Backend API | FastAPI + `sse-starlette` (SSE streaming) |
| Charts | Plotly → `react-plotly.js` in frontend |
| Memory | SQLite (`sqlite3` stdlib, no ORM) |
| Frontend | React (hooks, no heavier state library) |

---

## Getting started

> **Note:** Full setup instructions will be added when the project is complete. The project is currently under active development.

### Prerequisites

- Python ≥ 3.11
- A [Groq API key](https://console.groq.com/keys) (free tier works)
- Your Letterboxd diary export (Settings → Import & Export → Export Your Data)

### Setup

```bash
git clone https://github.com/AkileshD/BoxdBot.git
cd BoxdBot

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# Edit .env — add your GROQ_API_KEY
```

### Run tests

```bash
pytest tests/ -v
```

---

## Project structure

```
BoxdBot/
├── backend/
│   ├── memory/
│   │   └── db.py          # Episodic findings log (SQLite)
│   └── tools/
│       └── run_pandas.py  # Sandboxed code execution tool
├── tests/
│   ├── test_memory.py
│   └── test_run_pandas.py
├── pyproject.toml
└── .env.example
```

---

## What's deliberately not in scope

- No movie recommendations or trivia — answers come from your own logged data only.
- No hosted deployment — this is a local tool.
- No classical ML — fully LLM/agent-only.
- No agent framework (LangChain etc.) — the loop is built from scratch by design.

---

## License

MIT
