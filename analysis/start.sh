#!/bin/bash

# S&P 500 Analysis App - Launch Script
# Starts both Flask API and React dev server

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$PROJECT_DIR/web"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  S&P 500 Analysis App - Starting Services${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if dependencies are installed
if ! pip3 show flask >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip3 install -r "$PROJECT_DIR/requirements.txt"
fi

if [ ! -d "$WEB_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing Node dependencies...${NC}"
    cd "$WEB_DIR" && npm install
fi

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
