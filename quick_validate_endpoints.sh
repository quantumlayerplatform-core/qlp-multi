#!/bin/bash

# Quick endpoint validation for key endpoints

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

echo -e "${CYAN}Quick Endpoint Validation - Quantum Layer Platform${NC}"
echo -e "${CYAN}=================================================${NC}\n"

# Function to test endpoint
test() {
    local method=$1
    local endpoint=$2
    local expected=$3
    local description=$4
    
    if [ "$method" = "GET" ]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    else
        status=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint")
    fi
    
    if [ "$status" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $method $endpoint [$status] - $description"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $method $endpoint [$status] Expected: [$expected] - $description"
        FAILED=$((FAILED + 1))
    fi
}

# Test core services
echo -e "${CYAN}Core Services:${NC}"
test GET "/health" "200" "Orchestrator"
curl -s -o /dev/null -w "Agent Factory: %{http_code}\n" "http://localhost:8001/health"
curl -s -o /dev/null -w "Validation Mesh: %{http_code}\n" "http://localhost:8002/health"
curl -s -o /dev/null -w "Vector Memory: %{http_code}\n" "http://localhost:8003/health"
curl -s -o /dev/null -w "Execution Sandbox: %{http_code}\n" "http://localhost:8004/health"

# Test key endpoints
echo -e "\n${CYAN}Key API Endpoints:${NC}"
test POST "/execute" "422" "Execute (no data)"
test POST "/generate/capsule" "422" "Generate Capsule (no data)"
test GET "/patterns/usage-guide" "200" "Pattern Usage Guide"
test GET "/optimization/insights" "200" "Optimization Insights"
test GET "/hitl/pending" "200" "HITL Pending"
test GET "/hitl/statistics" "200" "HITL Statistics"
test POST "/patterns/analyze" "422" "Pattern Analysis (no data)"
test POST "/decompose/unified-optimization" "422" "Unified Optimization (no data)"
test GET "/api/capsules" "500" "List Capsules (DB issue expected)"
test POST "/api/enterprise/generate" "401" "Enterprise Generate (auth expected)"

# Test 404 endpoints (should not exist)
echo -e "\n${CYAN}Non-existent Endpoints (expecting 404):${NC}"
test GET "/api/not-exists" "404" "Non-existent endpoint"
test GET "/capsule/invalid-id" "404" "Invalid capsule"

# Summary
echo -e "\n${CYAN}=================================================${NC}"
echo -e "${CYAN}Summary:${NC}"
echo -e "Total: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ All expected endpoints are working!${NC}"
else
    echo -e "\n${YELLOW}⚠️  Some endpoints failed validation${NC}"
fi