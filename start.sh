#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
command -v python3.12 >/dev/null || { echo 'Python 3.12 is required'; exit 1; }
command -v npm >/dev/null || { echo 'Node.js 18+ and npm are required'; exit 1; }
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
(cd backend && ../backend/.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000) &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT
cd frontend
[ -d node_modules ] || npm install
npm run dev
