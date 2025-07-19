#\!/bin/bash

echo "🔍 Capsule Generation Comparison Test"
echo "======================================"

# Test data
REQUEST_DATA='{
  "tenant_id": "test-tenant",
  "user_id": "test-user",
  "description": "Create a Python function to calculate factorial of a number with tests"
}'

# Execute regular request
echo -e "\n=== EXECUTING REGULAR REQUEST ==="
REGULAR_RESPONSE=$(curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d "$REQUEST_DATA")

REGULAR_WORKFLOW_ID=$(echo "$REGULAR_RESPONSE" | grep -o '"workflow_id":"[^"]*' | cut -d'"' -f4)
echo "Regular workflow ID: $REGULAR_WORKFLOW_ID"

# Execute enterprise request
echo -e "\n=== EXECUTING ENTERPRISE REQUEST ==="
ENTERPRISE_RESPONSE=$(curl -s -X POST http://localhost:8000/execute/enterprise \
  -H "Content-Type: application/json" \
  -d "$REQUEST_DATA")

ENTERPRISE_WORKFLOW_ID=$(echo "$ENTERPRISE_RESPONSE" | grep -o '"workflow_id":"[^"]*' | cut -d'"' -f4)
echo "Enterprise workflow ID: $ENTERPRISE_WORKFLOW_ID"
echo "Enterprise features:"
echo "$ENTERPRISE_RESPONSE" | grep -o '"features":{[^}]*}' | sed 's/,/\n/g' | sed 's/{/{\n/g' | sed 's/}/\n}/g'

# Wait a bit for workflows to start
echo -e "\nWaiting for workflows to process..."
sleep 10

# Check status of both workflows
echo -e "\n=== WORKFLOW STATUS CHECK ==="
echo "Regular workflow status:"
curl -s http://localhost:8000/status/$REGULAR_WORKFLOW_ID | grep -o '"status":"[^"]*'

echo -e "\nEnterprise workflow status:"
curl -s http://localhost:8000/status/$ENTERPRISE_WORKFLOW_ID | grep -o '"status":"[^"]*'

# Wait more and check again
echo -e "\nWaiting 30 seconds for processing..."
sleep 30

echo -e "\n=== FINAL STATUS CHECK ==="
echo "Regular workflow status:"
curl -s http://localhost:8000/status/$REGULAR_WORKFLOW_ID

echo -e "\nEnterprise workflow status:"
curl -s http://localhost:8000/status/$ENTERPRISE_WORKFLOW_ID

