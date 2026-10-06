#!/usr/bin/env bash
# 
# Start the Library Management System backend server.
# Creates .env from .env.example if missing, seeds database, starts uvicorn.
# 

set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BACKEND_DIR"

echo "============================================================"
echo "  Library Management System - Backend Starting..."
echo "============================================================"
echo ""

# Check if .env exists, create from .env.example if not
if [ ! -f ".env" ]; then
    echo "[INFO] .env not found, creating from .env.example..."
    cp .env.example .env
    echo "[INFO] .env created. Please update JWT_SECRET before production use."
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "[INFO] Activating virtual environment..."
    source venv/bin/activate
else
    echo "[ERROR] Virtual environment not found. Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Seed database
echo "[INFO] Initializing database..."
if [ "$1" = "--reset" ]; then
    python seed_data.py --reset
else
    python seed_data.py
fi

if [ $? -ne 0 ]; then
    echo "[ERROR] Database seeding failed"
    exit 1
fi

# Start uvicorn server
echo ""
echo "============================================================"
echo "  Starting API server on http://0.0.0.0:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Health:   http://localhost:8000/health"
echo "============================================================"
echo ""

export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload