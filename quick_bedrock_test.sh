#!/bin/bash

echo "🧪 Quick AWS Bedrock Integration Test"
echo "===================================="
echo ""

# Submit a simple request
echo "1. Submitting code generation request..."
RESPONSE=$(curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python function to check if a number is prime",
    "language": "python",
    "tenant_id": "bedrock-test",
    "user_id": "test-user"
  }')

WORKFLOW_ID=$(echo "$RESPONSE" | grep -o '"workflow_id":"[^"]*' | cut -d'"' -f4)
echo "   Workflow ID: $WORKFLOW_ID"
echo ""

# Wait a bit
echo "2. Waiting for processing..."
sleep 10

# Check status
echo "3. Checking workflow status..."
STATUS=$(curl -s http://localhost:8000/status/$WORKFLOW_ID | python3 -m json.tool)
echo "$STATUS"
echo ""

# Check for AWS Bedrock in container environment
echo "4. Verifying AWS Bedrock configuration..."
docker exec qlp-agent-factory env | grep -E "(AWS_|LLM_)" | grep -E "(aws_bedrock|eu-west-2)" | head -5
echo ""

# Check Temporal UI
echo "5. Workflow Details:"
echo "   View in Temporal UI: http://localhost:8088/namespaces/default/workflows/$WORKFLOW_ID"
echo ""

echo "✅ Test submitted! AWS Bedrock should be processing the request."
echo "Check docker logs for detailed AWS Bedrock activity:"
echo "   docker logs qlp-agent-factory -f | grep -i bedrock"