#!/bin/bash

echo "🚀 Testing /execute endpoint with wait"
echo "====================================="
echo ""

# Test 1: Create a simple Python function
echo "1️⃣ Creating a Python web scraper..."
echo ""

RESPONSE=$(curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo",
    "user_id": "developer",
    "description": "Create a Python web scraper that extracts product information from e-commerce sites. Include functions to parse HTML, extract prices and titles, and save to JSON."
  }')

echo "Response:"
echo "$RESPONSE" | jq '.'

# Extract workflow_id
WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.workflow_id // empty')

if [ -n "$WORKFLOW_ID" ]; then
    echo ""
    echo "📋 Workflow submitted: $WORKFLOW_ID"
    echo "⏳ Waiting for completion (this may take 1-2 minutes)..."
    echo ""
    
    # Poll for workflow status
    MAX_ATTEMPTS=60
    ATTEMPT=0
    CAPSULE_ID=""
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        
        # Get workflow status
        STATUS_RESPONSE=$(curl -s http://localhost:8000/api/workflows/$WORKFLOW_ID/status)
        STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // empty')
        
        if [ "$STATUS" = "completed" ]; then
            CAPSULE_ID=$(echo "$STATUS_RESPONSE" | jq -r '.result.capsule_id // empty')
            echo "✅ Workflow completed! Capsule ID: $CAPSULE_ID"
            break
        elif [ "$STATUS" = "failed" ]; then
            echo "❌ Workflow failed!"
            echo "$STATUS_RESPONSE" | jq '.'
            exit 1
        else
            echo -n "."
            sleep 2
        fi
    done
    
    echo ""
    
    if [ -n "$CAPSULE_ID" ]; then
        # Get capsule details
        echo ""
        echo "2️⃣ Retrieving capsule details..."
        echo ""
        
        CAPSULE_DETAILS=$(curl -s http://localhost:8000/api/capsules/$CAPSULE_ID)
        
        echo "Capsule Summary:"
        echo "$CAPSULE_DETAILS" | jq '{
            id: .id,
            name: .manifest.name,
            language: .manifest.language,
            description: .manifest.description,
            files: (.source_code | keys),
            tests: (.tests | keys),
            validation_status: .validation_report.overall_status
        }'
        
        # Show file contents
        echo ""
        echo "📁 Source Files:"
        echo "$CAPSULE_DETAILS" | jq -r '.source_code | keys[]'
        
        # Test GitHub push if token is available
        if [ -n "$GITHUB_TOKEN" ]; then
            echo ""
            echo "3️⃣ Pushing to GitHub (Standard)..."
            echo ""
            
            REPO_NAME="qlp-web-scraper-$(date +%Y%m%d%H%M%S)"
            
            GITHUB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/v2 \
              -H "Content-Type: application/json" \
              -d "{
                \"capsule_id\": \"$CAPSULE_ID\",
                \"github_token\": \"$GITHUB_TOKEN\",
                \"repo_name\": \"$REPO_NAME\"
              }")
            
            REPO_URL=$(echo "$GITHUB_RESPONSE" | jq -r '.repository_url // empty')
            if [ -n "$REPO_URL" ]; then
                echo "✅ Repository created: $REPO_URL"
                echo "   Files: $(echo "$GITHUB_RESPONSE" | jq -r '.files_created')"
            else
                echo "❌ Failed to push:"
                echo "$GITHUB_RESPONSE" | jq '.'
            fi
            
            # Enterprise push
            echo ""
            echo "4️⃣ Pushing to GitHub (Enterprise)..."
            echo ""
            
            ENTERPRISE_REPO="qlp-web-scraper-enterprise-$(date +%Y%m%d%H%M%S)"
            
            ENTERPRISE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/enterprise \
              -H "Content-Type: application/json" \
              -d "{
                \"capsule_id\": \"$CAPSULE_ID\",
                \"github_token\": \"$GITHUB_TOKEN\",
                \"repo_name\": \"$ENTERPRISE_REPO\",
                \"use_enterprise_structure\": true
              }")
            
            ENTERPRISE_URL=$(echo "$ENTERPRISE_RESPONSE" | jq -r '.repository_url // empty')
            if [ -n "$ENTERPRISE_URL" ]; then
                echo "✅ Enterprise repository created: $ENTERPRISE_URL"
                echo "   Files: $(echo "$ENTERPRISE_RESPONSE" | jq -r '.files_created')"
            else
                echo "❌ Failed to push enterprise:"
                echo "$ENTERPRISE_RESPONSE" | jq '.'
            fi
            
            echo ""
            echo "📊 Comparison:"
            echo "   Standard repo: $REPO_URL"
            echo "   Enterprise repo: $ENTERPRISE_URL"
            
        else
            echo ""
            echo "⚠️  Skipping GitHub push (no GITHUB_TOKEN set)"
            echo "   To test GitHub push, run: export GITHUB_TOKEN=your_github_personal_access_token"
            echo ""
            echo "📌 You can manually push this capsule later with:"
            echo "   curl -X POST http://localhost:8000/api/github/push/v2 \\"
            echo "     -H 'Content-Type: application/json' \\"
            echo "     -d '{"
            echo "       \"capsule_id\": \"$CAPSULE_ID\","
            echo "       \"github_token\": \"\$GITHUB_TOKEN\","
            echo "       \"repo_name\": \"my-web-scraper\""
            echo "     }'"
        fi
    else
        echo "❌ Workflow did not produce a capsule"
    fi
else
    echo "❌ Failed to start workflow"
fi

echo ""
echo "✨ Test complete!"