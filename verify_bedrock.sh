#!/bin/bash

echo "🔍 Verifying AWS Bedrock Integration"
echo "===================================="
echo ""

# Check environment in containers
echo "1. AWS Configuration in Containers:"
echo "   Agent Factory:"
docker exec qlp-agent-factory printenv | grep -E "(AWS_|LLM_)" | grep -E "(REGION|PROVIDER|MODEL)" | sort
echo ""

# Submit a test that should use T2 (code generation)
echo "2. Submitting T2-level task (should use AWS Bedrock)..."
RESPONSE=$(curl -s -X POST http://localhost:8001/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Generate a Python class for a binary search tree with insert, search, and delete methods",
    "agent_type": "developer",
    "tier": "T2",
    "context": {
      "language": "python",
      "workflow_id": "bedrock-test-'$(date +%s)'"
    }
  }')

echo "Response from Agent Factory:"
echo "$RESPONSE" | python3 -m json.tool || echo "$RESPONSE"
echo ""

# Check recent logs
echo "3. Recent Agent Factory Activity:"
docker logs qlp-agent-factory --tail 20 2>&1 | grep -E "(Bedrock|bedrock|AWS|claude|provider|LLM)" -i || echo "No matching logs found"
echo ""

echo "✅ Verification complete!"
echo ""
echo "If AWS Bedrock is working, you should see:"
echo "- LLM_T2_PROVIDER=aws_bedrock in environment"
echo "- References to 'aws_bedrock' or 'claude' in the response"
echo "- AWS Bedrock activity in the logs"