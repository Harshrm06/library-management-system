#!/usr/bin/env bash
# 
# Start the Library Management System frontend development server.
# Installs dependencies if needed, starts Vite dev server.
# 

set -e

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$FRONTEND_DIR"

echo "============================================================"
echo "  Library Management System - Frontend Starting..."
echo "============================================================"
echo ""

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo "[INFO] node_modules not found, installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "[ERROR] npm install failed"
        exit 1
    fi
fi

# Start Vite dev server
echo ""
echo "============================================================"
echo "  Starting Vite dev server on http://localhost:5173"
echo "============================================================"
echo ""

npm run dev