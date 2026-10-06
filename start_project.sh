#!/usr/bin/env bash
# 
# Master startup script for Library Management System.
# Starts both backend and frontend in background.
# 

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "============================================================"
echo "  Library Management System Starting..."
echo "============================================================"
echo ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "[ERROR] Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "[ERROR] Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Start backend in background
echo "[INFO] Starting backend server..."
cd "$BACKEND_DIR"
./run.sh &
BACKEND_PID=$!

# Wait for backend to start
echo "[INFO] Waiting 5 seconds for backend to initialize..."
sleep 5

# Start frontend in background
echo "[INFO] Starting frontend server..."
cd "$FRONTEND_DIR"
./run.sh &
FRONTEND_PID=$!

# Wait a moment
sleep 2

echo ""
echo "============================================================"
echo "  Library Management System is running!"
echo "============================================================"
echo ""
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Default Credentials:"
echo "    Admin:    admin@library.local / Admin123"
echo "    Member:   member@library.local / Member123"
echo ""
echo "  Backend PID:  $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "  To stop: kill $BACKEND_PID $FRONTEND_PID"
echo "============================================================"

# Keep script running to show output
wait