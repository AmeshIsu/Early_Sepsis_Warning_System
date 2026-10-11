#!/usr/bin/env bash
set -e

echo "========================================================"
echo "  Starting SepsisWatch: ICU Early Warning System"
echo "========================================================"
echo ""

# 1. Install backend requirements
echo "[1/3] Checking Python dependencies..."
pip install -r backend/requirements.txt --quiet

# 2. Start Backend
echo "[2/3] Starting FastAPI Backend on http://127.0.0.1:8000..."
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 3. Start Frontend
echo "[3/3] Starting Vite Frontend on http://localhost:5173..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "========================================================"
echo "  SepsisWatch System Launched!"
echo "  Frontend: http://localhost:5173"
echo "  Backend API: http://127.0.0.1:8000/docs"
echo "========================================================"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
