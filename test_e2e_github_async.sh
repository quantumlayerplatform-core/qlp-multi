#!/bin/bash

# Test end-to-end flow with async workflow tracking

echo "🚀 Testing end-to-end flow with GitHub integration (async)..."
echo ""

# Start the workflow
echo "Starting workflow..."
RESPONSE=$(curl -s -X POST http://localhost:8000/generate/complete-with-github \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python CLI tool for task management. Include commands to add, list, complete, and delete tasks. Store tasks in a JSON file. Use argparse for command parsing.",
    "github_token": "'${GITHUB_TOKEN}'",
    "repo_name": "task-manager-cli",
    "private": false
  }')

echo "Initial response:"
echo "$RESPONSE" | jq '.'

# Extract workflow ID
WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow_id')
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

if [ "$SUCCESS" = "true" ]; then
    echo ""
    echo "✅ Workflow completed successfully!"
    echo "GitHub URL: $(echo "$RESPONSE" | jq -r '.github_url')"
else
    echo ""
    echo "⏳ Workflow is running. Workflow ID: $WORKFLOW_ID"
    echo "Checking status..."
    
    # Poll for status
    for i in {1..30}; do
        sleep 10
        echo -n "."
        
        STATUS_RESPONSE=$(curl -s http://localhost:8000/workflow/status/$WORKFLOW_ID)
        STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
        
        if [ "$STATUS" = "completed" ]; then
            echo ""
            echo "✅ Workflow completed!"
            echo "$STATUS_RESPONSE" | jq '.'
            break
        elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "terminated" ] || [ "$STATUS" = "canceled" ]; then
            echo ""
            echo "❌ Workflow $STATUS"
            echo "$STATUS_RESPONSE" | jq '.'
            break
        fi
        
        if [ $i -eq 30 ]; then
            echo ""
            echo "⏱️ Workflow still running after 5 minutes"
            echo "Latest status:"
            echo "$STATUS_RESPONSE" | jq '.'
        fi
    done
fi

echo ""
echo "Test complete!"