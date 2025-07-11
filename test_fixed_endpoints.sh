#!/bin/bash

# Integration tests for fixed endpoints

echo "🧪 Testing Fixed Endpoints"
echo "========================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test workflow status endpoint
echo -e "\n🔍 Testing Workflow Status Endpoint..."
# Start a simple workflow
RESPONSE=$(curl -s -X POST http://localhost:8000/generate/capsule \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-status-'$(date +%s)'",
    "tenant_id": "test",
    "user_id": "tester",
    "project_name": "Status Test",
    "description": "Hello world function",
    "requirements": "Print hello",
    "tech_stack": ["Python"]
  }')

WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow_id // empty')

if [ ! -z "$WORKFLOW_ID" ]; then
    echo "  Workflow ID: $WORKFLOW_ID"
    
    # Test status endpoint
    sleep 2
    STATUS_RESPONSE=$(curl -s http://localhost:8000/workflow/status/$WORKFLOW_ID)
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // empty')
    
    if [ ! -z "$STATUS" ]; then
        echo -e "  Status: $STATUS"
        echo -e "  ${GREEN}✅ Workflow status endpoint working!${NC}"
    else
        echo -e "  ${RED}❌ Status endpoint failed${NC}"
        echo "  Response: $STATUS_RESPONSE"
    fi
else
    echo -e "  ${RED}❌ Failed to start workflow${NC}"
fi

# Test CI confidence endpoint
echo -e "\n🎯 Testing CI/CD Confidence Endpoint..."
# First create a capsule
CAPSULE_RESPONSE=$(curl -s -X POST http://localhost:8000/generate/capsule \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-ci-'$(date +%s)'",
    "tenant_id": "test",
    "user_id": "tester",
    "project_name": "CI Test",
    "description": "Calculator",
    "requirements": "Basic math",
    "tech_stack": ["Python"]
  }')

CAPSULE_ID=$(echo "$CAPSULE_RESPONSE" | jq -r '.capsule_id // empty')

if [ ! -z "$CAPSULE_ID" ]; then
    echo "  Capsule ID: $CAPSULE_ID"
    
    # Wait for capsule to be stored
    sleep 3
    
    # Test CI confidence endpoint
    CI_RESPONSE=$(curl -s -X POST http://localhost:8000/api/capsule/$CAPSULE_ID/ci-confidence \
      -H "Content-Type: application/json" \
      -d '{"github_token": "'${GITHUB_TOKEN:-test-token}'"}'
    )
    
    if echo "$CI_RESPONSE" | jq -e '.original_confidence' >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ CI confidence endpoint working!${NC}"
    elif echo "$CI_RESPONSE" | jq -e '.detail' | grep -q "not been pushed to GitHub"; then
        echo -e "  ${GREEN}✅ CI endpoint works (capsule not on GitHub - expected)${NC}"
    else
        echo -e "  ${RED}❌ CI confidence endpoint failed${NC}"
        echo "  Response: $CI_RESPONSE"
    fi
else
    echo -e "  ${RED}❌ Failed to create capsule${NC}"
fi

# Test async GitHub endpoint
echo -e "\n⚡ Testing Async GitHub Endpoint..."
ASYNC_RESPONSE=$(curl -s -X POST http://localhost:8000/generate/complete-with-github \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Simple todo list",
    "github_token": "'${GITHUB_TOKEN:-test-token}'",
    "repo_name": "test-async-'$(date +%s)'",
    "private": true
  }')

ASYNC_WORKFLOW_ID=$(echo "$ASYNC_RESPONSE" | jq -r '.workflow_id // empty')
STATUS_URL=$(echo "$ASYNC_RESPONSE" | jq -r '.status_check_url // empty')

if [ ! -z "$ASYNC_WORKFLOW_ID" ] && [ ! -z "$STATUS_URL" ]; then
    echo "  Workflow ID: $ASYNC_WORKFLOW_ID"
    echo "  Status URL: $STATUS_URL"
    echo -e "  ${GREEN}✅ Async endpoint working correctly!${NC}"
else
    echo -e "  ${RED}❌ Async endpoint failed${NC}"
    echo "  Response: $ASYNC_RESPONSE"
fi

# Test GitHub error handling
echo -e "\n🔐 Testing GitHub Error Handling..."
ERROR_RESPONSE=$(curl -s -X POST http://localhost:8000/github/push/test-capsule-123 \
  -H "Content-Type: application/json" \
  -d '{
    "github_token": "invalid_token_12345",
    "repo_name": "test-error"
  }')

if echo "$ERROR_RESPONSE" | jq -e '.detail' | grep -qiE "(authentication|invalid|token)"; then
    echo -e "  ${GREEN}✅ Invalid token properly handled!${NC}"
else
    echo -e "  ${YELLOW}⚠️  Error handling may need improvement${NC}"
    echo "  Response: $ERROR_RESPONSE"
fi

echo -e "\n========================="
echo "🎉 Integration tests complete!"