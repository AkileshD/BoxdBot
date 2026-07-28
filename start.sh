#!/usr/bin/env bash
# start.sh — Run BoxdBot backend + frontend concurrently
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if it exists (provides GROQ_API_KEY, FINDINGS_DB_PATH)
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

echo ""
echo "  ██████╗  ██████╗ ██╗  ██╗██████╗ ██████╗  ██████╗ ████████╗"
echo "  ██╔══██╗██╔═══██╗╚██╗██╔╝██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝"
echo "  ██████╔╝██║   ██║ ╚███╔╝ ██║  ██║██████╔╝██║   ██║   ██║   "
echo "  ██╔══██╗██║   ██║ ██╔██╗ ██║  ██║██╔══██╗██║   ██║   ██║   "
echo "  ██████╔╝╚██████╔╝██╔╝ ██╗██████╔╝██████╔╝╚██████╔╝   ██║   "
echo "  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═════╝  ╚═════╝   ╚═╝   "
echo ""
echo "  Starting backend (FastAPI) on http://localhost:8000"
echo "  Starting frontend (Vite)   on http://localhost:5173"
echo ""

# Kill both processes on exit (Ctrl+C or error)
cleanup() {
  echo ""
  echo "  Shutting down BoxdBot..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo "  Done."
}
trap cleanup INT TERM EXIT

# Start backend
"$SCRIPT_DIR/.venv/bin/uvicorn" backend.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level warning &
BACKEND_PID=$!

# Wait a moment for backend to init before starting frontend
sleep 2

# Start frontend
cd "$SCRIPT_DIR/frontend"
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo "  ✓ Backend PID: $BACKEND_PID"
echo "  ✓ Frontend PID: $FRONTEND_PID"
echo ""
echo "  Opening http://localhost:5173 in your browser..."
echo "  Press Ctrl+C to stop both servers."
echo ""

# Open in default browser after a short delay to let Vite fully start
sleep 1 && open "http://localhost:5173" &

# Wait for either process to exit
wait -n 2>/dev/null || wait
