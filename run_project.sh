#!/usr/bin/env bash
# =============================================================================
#  Library Management System - start the API and the Vite dev server.
#
#  Usage (from anywhere):
#      ./run_project.sh            start both servers
#      ./run_project.sh --migrate  run "alembic upgrade head" first
#
#  Environment overrides:
#      HOST  interface uvicorn binds to (default 127.0.0.1)
#      PORT  API port (default 8000)
#
#  Prerequisite: MySQL must be running and the schema migrated, otherwise
#  every endpoint fails at runtime. See backend/.env.example for DATABASE_URL.
# =============================================================================
set -euo pipefail

# Resolve the project root from this script's own location, so the script works
# regardless of the directory it is launched from.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV_ACTIVATE="$BACKEND/.venv/bin/activate"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
MIGRATE=0
for arg in "$@"; do
    case "$arg" in
        --migrate) MIGRATE=1 ;;
        *) echo "[ERROR] Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

# --- prerequisite checks ----------------------------------------------------
if [ ! -x "$BACKEND/.venv/bin/python" ]; then
    echo "[ERROR] Backend virtual environment not found at $BACKEND/.venv" >&2
    echo "        Create it first:" >&2
    echo "            cd backend" >&2
    echo "            python3 -m venv .venv" >&2
    echo "            .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    echo "[ERROR] Node.js is not on PATH. Install Node 18+ first." >&2
    exit 1
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
    echo "[WARNING] frontend/node_modules is missing."
    echo "          Run 'npm install' in $FRONTEND first." >&2
    echo >&2
fi

if [ ! -f "$BACKEND/.env" ]; then
    echo "[WARNING] backend/.env not found - falling back to built-in defaults."
    echo "          JWT_SECRET will be the insecure \"change_me_in_production\" and"
    echo "          DATABASE_URL will be the placeholder MySQL URL."
    echo "          Copy backend/.env.example to backend/.env to fix this." >&2
    echo >&2
fi

# Activate the interpreter rather than relying on `uvicorn` being on PATH.
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"

# --- optional schema migration ----------------------------------------------
if [ "$MIGRATE" -eq 1 ]; then
    echo "[INFO] Applying database migrations..."
    (cd "$BACKEND" && python -m alembic upgrade head) \
        || { echo "[ERROR] Migration failed. Is MySQL running and reachable?" >&2; exit 1; }
    echo "[INFO] Migrations applied."
    echo
fi

# --- start both servers -----------------------------------------------------
# Track the PIDs so Ctrl-C stops the pair together; without this, killing the
# script would leave uvicorn and vite orphaned.
backend_pid=""
frontend_pid=""

cleanup() {
    echo
    echo "[INFO] Stopping servers..."
    [ -n "$frontend_pid" ] && kill "$frontend_pid" 2>/dev/null || true
    [ -n "$backend_pid" ] && kill "$backend_pid" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[INFO] Starting backend on http://$HOST:$PORT"
(cd "$BACKEND" && exec python -m uvicorn app.main:app --reload \
    --host "$HOST" --port "$PORT") &
backend_pid=$!

echo "[INFO] Starting frontend..."
(cd "$FRONTEND" && exec npm run dev) &
frontend_pid=$!

echo
echo "  Backend:  http://localhost:$PORT"
echo "  API docs: http://localhost:$PORT/docs"
echo "  Frontend: http://localhost:5173"
echo
echo "  Press Ctrl-C to stop both."
echo

# Plain `wait` rather than `wait -n <pids>`: the `-n` flag only accepts explicit
# job ids from bash 5.1, and macOS still ships bash 3.2 as /bin/bash, where the
# options form is rejected outright. Plain `wait` is POSIX and works everywhere.
wait
