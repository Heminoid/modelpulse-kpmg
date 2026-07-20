#!/bin/bash

echo "Starting ModelPulse Backend and Frontend..."

# Kill background processes on exit
trap 'kill 0' SIGINT

# Start Backend (FastAPI)
echo "Starting Backend on http://localhost:8000"
.venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start Frontend (Vite)
echo "Starting Frontend on http://localhost:5173"
cd frontend && npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait
