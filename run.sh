#!/bin/bash
cd "$(dirname "$0")"

# Find a free port (tries given list, then random)
find_free_port() {
  for port in "$@"; do
    if python3 -c "import socket; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('', $port)); s.close()" 2>/dev/null; then
      echo "$port"
      return
    fi
  done
  python3 -c "import socket; s=socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()"
}

cleanup() {
  kill $BACKEND_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

BACKEND_PORT=$(find_free_port 8000 8001 8002 8003 8004)
FRONTEND_PORT=$(find_free_port 5173 5174 5175 5176)
APP_URL="http://localhost:$FRONTEND_PORT"

echo "Using backend port $BACKEND_PORT, frontend port $FRONTEND_PORT"
echo ""

echo "Starting backend on port $BACKEND_PORT..."
pip install -q -r backend/requirements.txt 2>/dev/null
uvicorn backend.api:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

echo "Waiting for backend..."
sleep 3

# Open browser after frontend is ready
(sleep 5 && (xdg-open "$APP_URL" 2>/dev/null || open "$APP_URL" 2>/dev/null || true)) &

echo "Starting frontend on port $FRONTEND_PORT..."
echo "Browser will open at $APP_URL"
echo ""
cd frontend
npm install -q 2>/dev/null
VITE_API_BASE_URL="http://localhost:$BACKEND_PORT" npm run dev -- --port "$FRONTEND_PORT"

cleanup
