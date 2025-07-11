#!/bin/bash

echo "🚀 Testing Complete Flow: Execute → Push to GitHub"
echo "================================================="
echo ""

# Load environment variables
if [ -f ".env" ]; then
    echo "📄 Loading environment from .env..."
    source .env
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not found"
    exit 1
fi

echo "✅ GitHub token found"
echo ""

# Step 1: Create a simple capsule
echo "1️⃣ Creating a simple Python calculator..."

EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test",
    "user_id": "developer", 
    "description": "Create a simple Python calculator with add, subtract, multiply, and divide functions. Make it production-ready with error handling."
  }')

echo "Execute Response:"
echo "$EXECUTE_RESPONSE" | jq '.'

WORKFLOW_ID=$(echo "$EXECUTE_RESPONSE" | jq -r '.workflow_id // empty')

if [ -n "$WORKFLOW_ID" ]; then
    echo ""
    echo "⏳ Waiting for workflow to complete..."
    
    # Wait for completion (up to 3 minutes)
    for i in {1..90}; do
        echo -n "."
        sleep 2
        
        # Check workflow status - try to get results directly
        STATUS_RESPONSE=$(curl -s "http://localhost:8000/api/workflows/$WORKFLOW_ID/status" || echo '{}')
        STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // "unknown"')
        
        if [ "$STATUS" = "completed" ]; then
            echo ""
            echo "✅ Workflow completed!"
            
            # Get the capsule ID from the result
            CAPSULE_ID=$(echo "$STATUS_RESPONSE" | jq -r '.result.capsule_id // empty')
            if [ -n "$CAPSULE_ID" ]; then
                echo "📦 Capsule ID: $CAPSULE_ID"
                break
            fi
        elif [ "$STATUS" = "failed" ]; then
            echo ""
            echo "❌ Workflow failed!"
            echo "$STATUS_RESPONSE" | jq '.'
            exit 1
        fi
        
        # Also check if we can find the capsule by checking recent capsules
        if [ $((i % 15)) -eq 0 ]; then
            echo ""
            echo "   Checking for new capsules..."
        fi
    done
    
    # If we still don't have a capsule ID, try to find it another way
    if [ -z "$CAPSULE_ID" ]; then
        echo ""
        echo "⚠️  Workflow status unclear, but let's try to find the capsule..."
        
        # Check if we can list capsules to find the most recent one
        RECENT_CAPSULES=$(curl -s "http://localhost:8000/api/capsules" | jq -r '.[0].id // empty' 2>/dev/null || echo "")
        if [ -n "$RECENT_CAPSULES" ]; then
            CAPSULE_ID="$RECENT_CAPSULES"
            echo "📦 Found recent capsule: $CAPSULE_ID"
        else
            echo "❌ Could not find capsule ID"
            exit 1
        fi
    fi
    
    # Step 2: Push to GitHub
    if [ -n "$CAPSULE_ID" ]; then
        echo ""
        echo "2️⃣ Pushing to GitHub..."
        
        REPO_NAME="qlp-calculator-$(date +%Y%m%d%H%M%S)"
        
        GITHUB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/v2 \
          -H "Content-Type: application/json" \
          -d "{
            \"capsule_id\": \"$CAPSULE_ID\",
            \"github_token\": \"$GITHUB_TOKEN\",
            \"repo_name\": \"$REPO_NAME\"
          }")
        
        echo "GitHub Response:"
        echo "$GITHUB_RESPONSE" | jq '.'
        
        SUCCESS=$(echo "$GITHUB_RESPONSE" | jq -r '.success // false')
        if [ "$SUCCESS" = "true" ]; then
            REPO_URL=$(echo "$GITHUB_RESPONSE" | jq -r '.repository_url')
            echo ""
            echo "🎉 SUCCESS! Repository created: $REPO_URL"
            
            # Also try enterprise push
            echo ""
            echo "3️⃣ Trying enterprise push..."
            
            ENTERPRISE_REPO="qlp-calculator-enterprise-$(date +%Y%m%d%H%M%S)"
            
            ENTERPRISE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/enterprise \
              -H "Content-Type: application/json" \
              -d "{
                \"capsule_id\": \"$CAPSULE_ID\",
                \"github_token\": \"$GITHUB_TOKEN\",
                \"repo_name\": \"$ENTERPRISE_REPO\",
                \"use_enterprise_structure\": true
              }")
            
            echo "Enterprise Response:"
            echo "$ENTERPRISE_RESPONSE" | jq '.'
            
            ENTERPRISE_SUCCESS=$(echo "$ENTERPRISE_RESPONSE" | jq -r '.success // false')
            if [ "$ENTERPRISE_SUCCESS" = "true" ]; then
                ENTERPRISE_URL=$(echo "$ENTERPRISE_RESPONSE" | jq -r '.repository_url')
                echo ""
                echo "🏢 Enterprise repository created: $ENTERPRISE_URL"
            fi
            
        else
            echo ""
            echo "❌ GitHub push failed"
        fi
    fi
else
    echo "❌ Failed to start workflow"
fi

echo ""
echo "✨ Test complete!"