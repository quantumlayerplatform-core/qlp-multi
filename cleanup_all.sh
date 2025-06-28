#!/bin/bash

# Complete cleanup script for QLP

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Quantum Layer Platform - Complete Cleanup          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Function to kill processes on port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Killing processes on port $port: $pids${NC}"
        kill -9 $pids 2>/dev/null || true
        sleep 1
    fi
}

# Step 1: Kill all Python processes related to QLP
echo -e "\n${YELLOW}1. Stopping all QLP Python processes...${NC}"

# Kill specific service processes
pkill -f "src.orchestrator.main" 2>/dev/null || true
pkill -f "src.agents.main" 2>/dev/null || true
pkill -f "src.validation.main" 2>/dev/null || true
pkill -f "src.memory.main" 2>/dev/null || true
pkill -f "src.sandbox.main" 2>/dev/null || true
pkill -f "src.orchestrator.worker" 2>/dev/null || true

# Kill by port (more thorough)
for port in 8000 8001 8002 8003 8004; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

# Kill any uvicorn processes
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python -m src" 2>/dev/null || true

echo -e "${GREEN}✅ Python processes stopped${NC}"

# Step 2: Free up ports
echo -e "\n${YELLOW}2. Freeing up service ports...${NC}"
ports=(8000 8001 8002 8003 8004 7233 8233 5432 6379 6333 9092 3000 9090 16686 9000 9001)

for port in "${ports[@]}"; do
    kill_port $port
done

echo -e "${GREEN}✅ Ports freed${NC}"

# Step 3: Stop and remove all Docker containers
echo -e "\n${YELLOW}3. Cleaning up Docker containers...${NC}"

# Stop all QLP-related containers
docker ps -a | grep "qlp-" | awk '{print $1}' | xargs -r docker stop 2>/dev/null || true
docker ps -a | grep "qlp-" | awk '{print $1}' | xargs -r docker rm 2>/dev/null || true

# Also stop temporal containers
docker ps -a | grep "temporal" | awk '{print $1}' | xargs -r docker stop 2>/dev/null || true
docker ps -a | grep "temporal" | awk '{print $1}' | xargs -r docker rm 2>/dev/null || true

# Use docker-compose to ensure everything is down
cd infrastructure/docker 2>/dev/null && docker-compose -f docker-compose.local.yml down -v || true
cd ../.. 2>/dev/null || true

echo -e "${GREEN}✅ Docker containers cleaned${NC}"

# Step 4: Clean up PID files
echo -e "\n${YELLOW}4. Cleaning up PID files...${NC}"
rm -f .temporal_worker.pid
rm -f logs/*.pid 2>/dev/null || true
echo -e "${GREEN}✅ PID files removed${NC}"

# Step 5: Clean up log files (optional)
echo -e "\n${YELLOW}5. Cleaning up log files...${NC}"
echo -n "Do you want to clear log files? (y/N): "
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    rm -f logs/*.log 2>/dev/null || true
    echo -e "${GREEN}✅ Log files cleared${NC}"
else
    echo -e "${YELLOW}⚠️  Log files preserved${NC}"
fi

# Step 6: Final verification
echo -e "\n${YELLOW}6. Verifying cleanup...${NC}"
all_clear=true

# Check for any remaining processes
for service in "orchestrator" "agents" "validation" "memory" "sandbox" "temporal"; do
    if pgrep -f "$service" > /dev/null 2>&1; then
        echo -e "${RED}❌ Found remaining $service processes${NC}"
        all_clear=false
    fi
done

# Check for any remaining containers
if docker ps | grep -E "(qlp-|temporal)" > /dev/null 2>&1; then
    echo -e "${RED}❌ Found remaining Docker containers${NC}"
    all_clear=false
fi

if [ "$all_clear" = true ]; then
    echo -e "${GREEN}✅ All services successfully cleaned up${NC}"
else
    echo -e "${RED}⚠️  Some services may still be running${NC}"
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🧹 Cleanup complete! Ready for fresh start.${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
