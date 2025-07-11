#!/bin/bash

echo "🚀 Testing /execute endpoint"
echo "=========================="
echo ""

# Test 1: Create a simple Python function
echo "1️⃣ Creating a simple Python calculator..."
echo ""

RESPONSE=$(curl -s -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test",
    "user_id": "developer",
    "description": "Create a Python calculator class with methods for add, subtract, multiply, and divide. Include error handling for division by zero."
  }')

echo "Response:"
echo "$RESPONSE" | jq '.'

# Extract capsule_id if successful
CAPSULE_ID=$(echo "$RESPONSE" | jq -r '.capsule_id // empty')

if [ -n "$CAPSULE_ID" ]; then
    echo ""
    echo "✅ Capsule created successfully!"
    echo "   Capsule ID: $CAPSULE_ID"
    echo ""
    
    # Get capsule details
    echo "2️⃣ Retrieving capsule details..."
    echo ""
    
    CAPSULE_DETAILS=$(curl -s http://localhost:8000/api/capsules/$CAPSULE_ID)
    
    echo "Capsule Details:"
    echo "$CAPSULE_DETAILS" | jq '{
        id: .id,
        name: .manifest.name,
        language: .manifest.language,
        files: (.source_code | keys),
        tests: (.tests | keys)
    }'
    
    # Show first file content (truncated)
    echo ""
    echo "📄 Sample code (first 20 lines):"
    echo "$CAPSULE_DETAILS" | jq -r '.source_code | to_entries | .[0].value' | head -20
    
    # Test GitHub push if token is available
    if [ -n "$GITHUB_TOKEN" ]; then
        echo ""
        echo "3️⃣ Pushing to GitHub..."
        echo ""
        
        GITHUB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/v2 \
          -H "Content-Type: application/json" \
          -d "{
            \"capsule_id\": \"$CAPSULE_ID\",
            \"github_token\": \"$GITHUB_TOKEN\",
            \"repo_name\": \"qlp-calculator-$(date +%Y%m%d%H%M%S)\"
          }")
        
        echo "GitHub Response:"
        echo "$GITHUB_RESPONSE" | jq '.'
        
        REPO_URL=$(echo "$GITHUB_RESPONSE" | jq -r '.repository_url // empty')
        if [ -n "$REPO_URL" ]; then
            echo ""
            echo "✅ Repository created: $REPO_URL"
        fi
        
        # Also test enterprise push
        echo ""
        echo "4️⃣ Testing enterprise push..."
        echo ""
        
        ENTERPRISE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/enterprise \
          -H "Content-Type: application/json" \
          -d "{
            \"capsule_id\": \"$CAPSULE_ID\",
            \"github_token\": \"$GITHUB_TOKEN\",
            \"repo_name\": \"qlp-calculator-enterprise-$(date +%Y%m%d%H%M%S)\",
            \"use_enterprise_structure\": true
          }")
        
        echo "Enterprise GitHub Response:"
        echo "$ENTERPRISE_RESPONSE" | jq '.'
        
        ENTERPRISE_URL=$(echo "$ENTERPRISE_RESPONSE" | jq -r '.repository_url // empty')
        if [ -n "$ENTERPRISE_URL" ]; then
            echo ""
            echo "✅ Enterprise repository created: $ENTERPRISE_URL"
        fi
    else
        echo ""
        echo "⚠️  Skipping GitHub push (no GITHUB_TOKEN set)"
        echo "   To test GitHub push, run: export GITHUB_TOKEN=your_token"
    fi
else
    echo ""
    echo "❌ Failed to create capsule"
fi

echo ""
echo "✨ Test complete!"