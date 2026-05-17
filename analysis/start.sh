#!/bin/bash

# S&P 500 Analysis App - Launch Script
# Starts both Flask API and React dev server

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$PROJECT_DIR/web"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse flags
NO_KILL=0
for arg in "$@"; do
    case "$arg" in
        --no-kill) NO_KILL=1 ;;
        -h|--help)
            echo "Usage: $0 [--no-kill]"
            echo "  --no-kill   Abort if :5001 or :5173 is already bound (default: kill stale process)"
            exit 0 ;;
    esac
done

# Ensure a port is free. If a process is already bound, either abort (--no-kill)
# or print a clear warning with PID + start time, then kill -TERM (5s grace, then -9).
free_port() {
    local port=$1
    local label=$2
    local pid
    pid=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -1)
    [ -z "$pid" ] && return 0

    local started
    started=$(ps -o lstart= -p "$pid" 2>/dev/null | sed 's/^ *//')
    echo -e "${YELLOW}!${NC} Port ${port} (${label}) already in use by PID ${pid} (started ${started})"

    if [ "$NO_KILL" = "1" ]; then
        echo -e "${RED}Aborting because --no-kill was passed.${NC}"
        echo -e "${RED}Either kill PID ${pid} manually or re-run without --no-kill.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}  Sending TERM…${NC}"
    kill -TERM "$pid" 2>/dev/null
    for _ in 1 2 3 4 5; do
        sleep 1
        lsof -ti tcp:"$port" -sTCP:LISTEN >/dev/null 2>&1 || { echo -e "${GREEN}  Port ${port} now free.${NC}"; return 0; }
    done
    echo -e "${YELLOW}  Still alive after 5s; sending KILL…${NC}"
    kill -9 "$pid" 2>/dev/null
    sleep 1
    if lsof -ti tcp:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        echo -e "${RED}  Failed to free port ${port}; aborting.${NC}"
        exit 1
    fi
    echo -e "${GREEN}  Port ${port} now free.${NC}"
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  S&P 500 Analysis App - Starting Services${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if dependencies are installed
if ! pip3 show flask >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
fi

if [ ! -d "$WEB_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing Node dependencies...${NC}"
    cd "$WEB_DIR" && npm install
fi

# Free ports before launching so we never silently leave a stale process serving.
free_port 5001 "Flask API"
free_port 5173 "Vite dev server"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $FLASK_PID $VITE_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start Flask API
echo -e "${GREEN}▶ Starting Flask API on http://localhost:5001${NC}"
cd "$PROJECT_DIR"
python3 app.py &
FLASK_PID=$!

# Give Flask a moment to start
sleep 2

# Start React dev server
echo -e "${GREEN}▶ Starting React app on http://localhost:5173${NC}"
cd "$WEB_DIR"
npm run dev &
VITE_PID=$!

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Services running!${NC}"
echo -e "  • Flask API:  ${BLUE}http://localhost:5001${NC}"
echo -e "  • React App:  ${BLUE}http://localhost:5173${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Wait for either process to exit
wait
