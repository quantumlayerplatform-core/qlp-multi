#!/bin/bash

# Complete startup script for QLP with Temporal

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Quantum Layer Platform - Complete Startup          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Function to check if a service is healthy
check_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $service on port $port...${NC}"
    
    while ! nc -z localhost $port 2>/dev/null; do
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${RED}❌ $service failed to start on port $port${NC}"
            return 1
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo -e "\n${GREEN}✅ $service is ready${NC}"
    return 0
}

# Step 1: Start infrastructure services
echo -e "\n${YELLOW}1. Starting infrastructure services...${NC}"
cd infrastructure/docker
docker-compose -f docker-compose.local.yml up -d

# Wait for critical services
check_service "PostgreSQL" 5432
check_service "Redis" 6379
check_service "Qdrant" 6333
check_service "Temporal" 7233

echo -e "${GREEN}✅ Infrastructure services are running${NC}"

# Step 2: Activate Python environment
cd ../..
echo -e "\n${YELLOW}2. Activating Python environment...${NC}"
if [[ "$VIRTUAL_ENV" == "" ]]; then
    source venv/bin/activate
fi
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Step 3: Start QLP microservices
echo -e "\n${YELLOW}3. Starting QLP microservices...${NC}"
./start.sh

# Give services time to start
sleep 5

# Step 4: Check all services are running
echo -e "\n${YELLOW}4. Verifying all services...${NC}"
services=(
    "Orchestrator:8000"
    "Agent Factory:8001"
    "Validation Mesh:8002"
    "Vector Memory:8003"
    "Execution Sandbox:8004"
)

all_healthy=true
for service_info in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_info"
    if ! check_service "$service" "$port"; then
        all_healthy=false
    fi
done

if [ "$all_healthy" = false ]; then
    echo -e "${RED}❌ Some services failed to start${NC}"
    exit 1
fi

# Step 5: Start Temporal worker
echo -e "\n${YELLOW}5. Starting Temporal worker...${NC}"
echo -e "${YELLOW}Starting worker in background...${NC}"
nohup python -m src.orchestrator.worker > logs/temporal_worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > .temporal_worker.pid
echo -e "${GREEN}✅ Temporal worker started (PID: $WORKER_PID)${NC}"

# Final status
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Quantum Layer Platform is fully operational!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}Service URLs:${NC}"
echo -e "  • Orchestrator API:    http://localhost:8000/docs"
echo -e "  • Agent Factory API:   http://localhost:8001/docs"
echo -e "  • Validation API:      http://localhost:8002/docs"
echo -e "  • Memory API:          http://localhost:8003/docs"
echo -e "  • Sandbox API:         http://localhost:8004/docs"
echo -e "  • Temporal UI:         http://localhost:8233"
echo -e "  • Grafana:             http://localhost:3000 (admin/admin)"
echo -e "  • Prometheus:          http://localhost:9090"
echo -e "  • Jaeger UI:           http://localhost:16686"
echo -e "  • MinIO Console:       http://localhost:9001 (minioadmin/minioadmin)"

echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "  1. Test the platform:  python test_integration.py"
echo -e "  2. Test Temporal:      python test_temporal.py"
echo -e "  3. Monitor logs:       tail -f logs/*.log"
echo -e "  4. Stop everything:    ./stop_all.sh"

echo -e "\n${GREEN}Happy coding! 🎯${NC}"
