#!/bin/bash

# Production-ready Temporal worker startup script for QLP

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Quantum Layer Platform Temporal Worker...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found. Please run 'python3 -m venv venv' first.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Temporal is running
if ! curl -s http://localhost:7233 > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Temporal server doesn't appear to be running on localhost:7233${NC}"
    echo "Attempting to start Temporal..."
    
    if [ -f "../qlp-multi/docker-compose.temporal.yml" ]; then
        docker-compose -f ../qlp-multi/docker-compose.temporal.yml up -d
        echo "Waiting for Temporal to start..."
        sleep 10
    else
        echo -e "${RED}Error: Cannot find Temporal docker-compose file${NC}"
        exit 1
    fi
fi

# Export Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check which worker to use
if [ "$1" == "production" ]; then
    echo -e "${GREEN}Starting production worker...${NC}"
    python -m src.orchestrator.worker_production
else
    echo -e "${GREEN}Starting standard worker...${NC}"
    # Use the production worker by default as it has better imports
    python -m src.orchestrator.worker_production
fi