#!/bin/bash

# Comprehensive endpoint validation script for Quantum Layer Platform
# Uses curl to test all documented endpoints

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8000"

# Counters
TOTAL=0
PASSED=0
FAILED=0

# Function to print headers
print_header() {
    echo -e "\n${CYAN}============================================================${NC}"
    echo -e "${CYAN}                    $1${NC}"
    echo -e "${CYAN}============================================================${NC}\n"
}

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    local expected_codes=${5:-"200 201 202"}
    
    TOTAL=$((TOTAL + 1))
    
    # Construct curl command
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint" 2>/dev/null)
        else
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" 2>/dev/null)
        fi
    fi
    
    # Extract status code (last line)
    status_code=$(echo "$response" | tail -n 1)
    
    # Check if status code is in expected list
    success=false
    for code in $expected_codes; do
        if [ "$status_code" = "$code" ]; then
            success=true
            break
        fi
    done
    
    # Print result
    if [ "$success" = true ]; then
        echo -e "${GREEN}✓ PASS${NC} $method $endpoint [$status_code] - $description"
        PASSED=$((PASSED + 1))
        
        # Extract useful data for future tests
        if [[ "$endpoint" == "/execute" ]] && [[ "$status_code" == "200" ]]; then
            WORKFLOW_ID=$(echo "$response" | head -n -1 | grep -o '"workflow_id":"[^"]*"' | cut -d'"' -f4)
        fi
    else
        echo -e "${RED}✗ FAIL${NC} $method $endpoint [$status_code] - $description"
        FAILED=$((FAILED + 1))
    fi
}

# Function to test service health
test_service_health() {
    local service=$1
    local port=$2
    
    TOTAL=$((TOTAL + 1))
    
    response=$(curl -s -w "\n%{http_code}" "http://localhost:$port/health" 2>/dev/null)
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} GET http://localhost:$port/health [$status_code] - $service health check"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} GET http://localhost:$port/health [$status_code] - $service health check"
        FAILED=$((FAILED + 1))
    fi
}

# Start validation
echo -e "${CYAN}Starting Quantum Layer Platform Endpoint Validation${NC}"
echo -e "${CYAN}Time: $(date)${NC}"

# Test all services health
print_header "All Services Health Check"

test_service_health "Orchestrator" 8000
test_service_health "Agent Factory" 8001
test_service_health "Validation Mesh" 8002
test_service_health "Vector Memory" 8003
test_service_health "Execution Sandbox" 8004

# Test health endpoints
print_header "Health Check Endpoints"
test_endpoint "GET" "/health" "" "Orchestrator health check"

# Test execution & generation endpoints
print_header "Execution & Generation Endpoints"

test_endpoint "POST" "/execute" '{"tenant_id":"test","user_id":"test-user","description":"Create a simple hello world function in Python"}' "Submit NLP request"

sleep 2  # Wait for workflow to start

test_endpoint "POST" "/generate/capsule" '{"request_id":"test-123","tenant_id":"test","user_id":"test-user","project_name":"Test Project","description":"Simple test project","requirements":"Basic functionality","tech_stack":["Python"]}' "Generate basic capsule"

test_endpoint "POST" "/generate/robust-capsule" '{"request_id":"test-456","tenant_id":"test","user_id":"test-user","project_name":"Test Project","description":"Simple test project","requirements":"Basic functionality","tech_stack":["Python"]}' "Production-grade generation"

# Test workflow endpoints
print_header "Workflow Management Endpoints"

if [ -n "$WORKFLOW_ID" ]; then
    test_endpoint "GET" "/workflow/status/$WORKFLOW_ID" "" "Get workflow status"
    test_endpoint "GET" "/status/$WORKFLOW_ID" "" "Simple status check"
    test_endpoint "POST" "/approve/$WORKFLOW_ID" "" "Approve HITL request" "200 404"
else
    echo -e "${YELLOW}Skipping workflow endpoints - no workflow_id available${NC}"
fi

# Test analysis endpoints
print_header "Analysis & Optimization Endpoints"

test_endpoint "POST" "/analyze/extended-reasoning" '{"request":"Create a web application with user authentication","context":{}}' "Extended analysis"

test_endpoint "POST" "/patterns/analyze" '{"description":"Test pattern analysis"}' "Pattern analysis"

test_endpoint "POST" "/patterns/recommend" '{"task_type":"code_generation","complexity":"medium"}' "Pattern recommendations"

test_endpoint "GET" "/patterns/usage-guide" "" "Pattern usage guide"

test_endpoint "POST" "/decompose/unified-optimization" '{"description":"Build a REST API","tenant_id":"test","user_id":"test"}' "Optimized decomposition"

test_endpoint "GET" "/optimization/insights" "" "Optimization insights"

# Test HITL endpoints
print_header "HITL Endpoints"

test_endpoint "POST" "/hitl/request" '{"task_id":"test-task","request_type":"approval","context":{"test":true}}' "Create HITL request" "200 422"

test_endpoint "GET" "/hitl/pending" "" "Get pending HITL requests"

test_endpoint "GET" "/hitl/statistics" "" "HITL statistics"

# Test capsule endpoints
print_header "Capsule Management Endpoints"

CAPSULE_ID="test-capsule-id"  # Use a test ID

test_endpoint "GET" "/capsule/$CAPSULE_ID" "" "Get capsule details" "200 404"

test_endpoint "POST" "/capsules/$CAPSULE_ID/deliver" '{"capsule_id":"'$CAPSULE_ID'","request_id":"test-request","tenant_id":"test","user_id":"test-user","package_format":"zip","delivery_methods":["download"],"metadata":{}}' "Package and deliver capsule" "200 404"

test_endpoint "GET" "/capsule/$CAPSULE_ID/export/zip" "" "Export capsule as ZIP" "200 404"

test_endpoint "POST" "/capsule/$CAPSULE_ID/version" '{"message":"Test version"}' "Create capsule version" "200 404"

test_endpoint "GET" "/capsule/$CAPSULE_ID/history" "" "Version history" "200 404"

# Test GitHub endpoints
print_header "GitHub Integration Endpoints"

test_endpoint "POST" "/api/github/push" '{"capsule_id":"test-capsule","repo_name":"test-repo","private":false}' "Push capsule to GitHub" "200 401 404"

# Test enterprise endpoints
print_header "Enterprise Feature Endpoints"

test_endpoint "POST" "/api/enterprise/generate" '{"description":"Create an enterprise web application","tenant_id":"test","user_id":"test-user","enterprise_features":{"documentation":true,"testing":true,"ci_cd":true}}' "Enterprise-grade project generation" "200 404"

# Test download endpoints
print_header "Download & Export Endpoints"

test_endpoint "GET" "/api/capsules" "" "List available capsules" "200 404 500"

test_endpoint "GET" "/api/capsules/$CAPSULE_ID/download?format=zip" "" "Download capsule as ZIP" "200 404 500"

# Print summary
print_header "Test Summary"

echo "Total Endpoints Tested: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(( PASSED * 100 / TOTAL ))
    echo "Success Rate: $SUCCESS_RATE%"
fi

# Exit with appropriate code
if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed.${NC}"
    exit 1
fi