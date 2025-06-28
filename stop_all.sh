#!/bin/bash

# Complete shutdown script for QLP with Temporal

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Quantum Layer Platform - Complete Shutdown         ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Step 1: Stop Temporal worker
echo -e "\n${YELLOW}1. Stopping Temporal worker...${NC}"
if [ -f .temporal_worker.pid ]; then
    WORKER_PID=$(cat .temporal_worker.pid)
    if kill -0 $WORKER_PID 2>/dev/null; then
        kill $WORKER_PID
        echo -e "${GREEN}✅ Temporal worker stopped (PID: $WORKER_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Worker process not found${NC}"
    fi
    rm .temporal_worker.pid
else
    echo -e "${YELLOW}⚠️  No worker PID file found${NC}"
fi

# Step 2: Stop QLP microservices
echo -e "\n${YELLOW}2. Stopping QLP microservices...${NC}"
./stop_platform.sh

# Step 3: Stop infrastructure services
echo -e "\n${YELLOW}3. Stopping infrastructure services...${NC}"
cd infrastructure/docker
docker-compose -f docker-compose.local.yml down
cd ../..

echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All services stopped successfully${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
