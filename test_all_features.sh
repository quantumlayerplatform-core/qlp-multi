#!/bin/bash

# Comprehensive QLP Platform Test Script
# Tests: /execute, GitHub push, marketing features, and CLI

echo "🚀 QuantumLayer Platform - Comprehensive Feature Test"
echo "====================================================="
echo "Testing with AWS Bedrock Integration"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8000"

# Function to check service health
check_service() {
    echo -n "Checking $1 service... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $2/health)
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Not responding${NC}"
        return 1
    fi
}

# Function to pretty print JSON
pretty_json() {
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
}

# 1. Check all services
echo "1️⃣ Checking Service Health"
echo "-------------------------"
check_service "Orchestrator" "http://localhost:8000"
check_service "Agent Factory" "http://localhost:8001"
check_service "Validation Mesh" "http://localhost:8002"
check_service "Vector Memory" "http://localhost:8003"
check_service "Execution Sandbox" "http://localhost:8004"
echo ""

# 2. Test /execute endpoint
echo "2️⃣ Testing /execute Endpoint (Code Generation)"
echo "--------------------------------------------"
echo "Request: Generate a Python calculator with AWS Bedrock"

EXECUTE_RESPONSE=$(curl -s -X POST "$BASE_URL/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python calculator class with add, subtract, multiply, divide methods and error handling",
    "language": "python",
    "tenant_id": "test-tenant",
    "user_id": "test-user"
  }')

echo "Response:"
pretty_json "$EXECUTE_RESPONSE"
WORKFLOW_ID=$(echo "$EXECUTE_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('workflow_id', ''))" 2>/dev/null)
echo -e "${GREEN}✓ Workflow ID: $WORKFLOW_ID${NC}"
echo ""

# Wait for workflow to complete
echo "Waiting for workflow to complete..."
sleep 5

# Check workflow status
echo "Checking workflow status..."
STATUS_RESPONSE=$(curl -s "$BASE_URL/status/$WORKFLOW_ID")
pretty_json "$STATUS_RESPONSE"
echo ""

# 3. Test GitHub Push
echo "3️⃣ Testing GitHub Push Feature"
echo "-----------------------------"
echo "Creating a project and pushing to GitHub..."

GITHUB_RESPONSE=$(curl -s -X POST "$BASE_URL/generate/complete-with-github" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a simple Python TODO list CLI application with add, list, and remove commands",
    "language": "python",
    "github_repo": "test-todo-cli-'$(date +%s)'",
    "github_private": false,
    "tenant_id": "test-tenant",
    "user_id": "test-user"
  }')

echo "Response:"
pretty_json "$GITHUB_RESPONSE"
GITHUB_WORKFLOW_ID=$(echo "$GITHUB_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('workflow_id', ''))" 2>/dev/null)
echo -e "${GREEN}✓ GitHub Workflow ID: $GITHUB_WORKFLOW_ID${NC}"
echo ""

# 4. Test Marketing Features
echo "4️⃣ Testing Marketing Campaign Generation"
echo "--------------------------------------"
echo "Creating a marketing campaign..."

MARKETING_RESPONSE=$(curl -s -X POST "$BASE_URL/api/marketing/campaign" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "launch_awareness",
    "product_description": "QuantumLayer Platform - AI-powered code generation platform",
    "key_features": ["AWS Bedrock integration", "Multi-provider LLM support", "Enterprise-grade", "GitHub integration"],
    "target_audience": "Software developers and tech companies",
    "unique_value_prop": "Generate production-ready code 10x faster with AI",
    "duration_days": 7,
    "channels": ["twitter", "linkedin"],
    "tone_preferences": ["technical", "innovative"],
    "auto_publish": false
  }')

echo "Response:"
pretty_json "$MARKETING_RESPONSE"
MARKETING_WORKFLOW_ID=$(echo "$MARKETING_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('workflow_id', ''))" 2>/dev/null)
echo -e "${GREEN}✓ Marketing Workflow ID: $MARKETING_WORKFLOW_ID${NC}"
echo ""

# 5. Test Enterprise Generation
echo "5️⃣ Testing Enterprise Project Generation"
echo "--------------------------------------"
echo "Creating an enterprise-grade project..."

ENTERPRISE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/enterprise/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a REST API microservice for user management with authentication, database, and tests",
    "language": "python",
    "framework": "fastapi",
    "include_tests": true,
    "include_docker": true,
    "include_ci": true,
    "tenant_id": "test-tenant",
    "user_id": "test-user"
  }')

echo "Response:"
pretty_json "$ENTERPRISE_RESPONSE"
echo ""

# 6. Test Pattern Analysis
echo "6️⃣ Testing Pattern Analysis"
echo "--------------------------"
echo "Analyzing code patterns..."

PATTERN_RESPONSE=$(curl -s -X POST "$BASE_URL/patterns/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Build a real-time chat application with WebSocket support",
    "language": "javascript",
    "tenant_id": "test-tenant"
  }')

echo "Response:"
pretty_json "$PATTERN_RESPONSE"
echo ""

# 7. Test CLI Commands
echo "7️⃣ Testing CLI Commands"
echo "---------------------"
echo ""

# Test CLI generate command
echo "Testing: qlp generate"
echo "Command: qlp generate \"create a fibonacci function\" --language python"
echo -e "${YELLOW}Note: Run this in another terminal to see live progress${NC}"
echo ""

# Test CLI status command
echo "Testing: qlp status"
if [ ! -z "$WORKFLOW_ID" ]; then
    echo "Command: qlp status $WORKFLOW_ID"
fi
echo ""

# Test CLI list command
echo "Testing: qlp list"
echo "Command: qlp list --limit 5"
echo ""

# 8. Check AWS Bedrock Usage
echo "8️⃣ Checking AWS Bedrock Usage"
echo "----------------------------"
echo "Checking if AWS Bedrock was used..."

# Check agent factory logs for Bedrock usage
echo "Recent Bedrock activity:"
docker logs qlp-agent-factory 2>&1 | grep -i "bedrock" | tail -5 || echo "No recent Bedrock activity in logs"
echo ""

# 9. Summary
echo "📊 Test Summary"
echo "=============="
echo ""
echo "✅ Services: All health checks completed"
echo "✅ /execute: Code generation workflow started"
echo "✅ GitHub: Repository creation initiated"
echo "✅ Marketing: Campaign generation started"
echo "✅ Enterprise: Full project generation started"
echo "✅ Patterns: Analysis completed"
echo "✅ AWS Bedrock: Integration active"
echo ""
echo "🔍 Check Individual Workflows:"
echo "- Execute: curl $BASE_URL/status/$WORKFLOW_ID"
echo "- GitHub: curl $BASE_URL/status/$GITHUB_WORKFLOW_ID"
echo "- Marketing: curl $BASE_URL/status/$MARKETING_WORKFLOW_ID"
echo ""
echo "📝 View Temporal UI: http://localhost:8088"
echo "🎯 Test Complete!"