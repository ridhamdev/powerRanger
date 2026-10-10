#!/usr/bin/env bash
# Power Grid Simulator: Single-Command All-in-One Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "============================================================"
echo "  Power Grid Simulator — Starting Backend and Frontend"
echo "============================================================"

# Stop any lingering processes on ports 5000 or 3000
fuser -k 5000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true

# 1. Start Flask Backend
echo "[1/2] Starting Flask Backend (port 5000)..."
cd "$DIR/backend"
if [ ! -d "venv" ]; then
    echo "      Setting up Python virtual environment..."
    python3 -m venv venv
    venv/bin/pip install -q -r requirements.txt
fi

venv/bin/python3 app.py > /dev/null 2>&1 &
BACKEND_PID=$!
echo "      Backend running (PID: $BACKEND_PID)"

# Trap Ctrl+C to shut down cleanly
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    echo "Done."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 2. Start React Frontend
echo "[2/2] Starting React Frontend (port 3000)..."
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "      Installing frontend packages (first time only)..."
    npm install --silent
fi

# Automatically open browser
(sleep 1.5 && (xdg-open http://localhost:3000 || sensible-browser http://localhost:3000 || true) > /dev/null 2>&1) &

echo "============================================================"
echo "  Ready! Open: http://localhost:3000"
echo "  Press Ctrl+C at any time to stop both servers."
echo "============================================================"

npm run dev
