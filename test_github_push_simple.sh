#!/bin/bash

echo "🚀 Testing GitHub Push with Existing Capsule"
echo "============================================"
echo ""

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env file..."
    source .env
fi

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not set. Please run:"
    echo "   export GITHUB_TOKEN=your_github_personal_access_token"
    echo "   Or add GITHUB_TOKEN to your .env file"
    exit 1
fi

echo "✅ GitHub token found (length: ${#GITHUB_TOKEN})"
echo ""

# Test with the capsule we know exists from the conversation
CAPSULE_ID="05590339-48ea-4702-b44a-8d67c406b0aa"

echo "📦 Testing with capsule: $CAPSULE_ID"
echo ""

# Test 1: Standard GitHub push
echo "1️⃣ Testing standard GitHub push..."
REPO_NAME="qlp-test-$(date +%Y%m%d%H%M%S)"

RESPONSE=$(curl -s -X POST http://localhost:8000/api/github/push/v2 \
  -H "Content-Type: application/json" \
  -d "{
    \"capsule_id\": \"$CAPSULE_ID\",
    \"github_token\": \"$GITHUB_TOKEN\",
    \"repo_name\": \"$REPO_NAME\"
  }")

echo "Response:"
echo "$RESPONSE" | jq '.'

SUCCESS=$(echo "$RESPONSE" | jq -r '.success // false')
if [ "$SUCCESS" = "true" ]; then
    REPO_URL=$(echo "$RESPONSE" | jq -r '.repository_url')
    FILES_COUNT=$(echo "$RESPONSE" | jq -r '.files_created')
    echo ""
    echo "✅ Standard push successful!"
    echo "   Repository: $REPO_URL"
    echo "   Files created: $FILES_COUNT"
else
    echo ""
    echo "❌ Standard push failed"
fi

echo ""
echo "───────────────────────────────────────────────"
echo ""

# Test 2: Enterprise GitHub push
echo "2️⃣ Testing enterprise GitHub push..."
ENTERPRISE_REPO="qlp-enterprise-$(date +%Y%m%d%H%M%S)"

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
    ENTERPRISE_FILES=$(echo "$ENTERPRISE_RESPONSE" | jq -r '.files_created')
    echo ""
    echo "✅ Enterprise push successful!"
    echo "   Repository: $ENTERPRISE_URL"
    echo "   Files created: $ENTERPRISE_FILES"
else
    echo ""
    echo "❌ Enterprise push failed"
fi

echo ""
echo "📊 Summary:"
echo "Standard repo: $(echo "$RESPONSE" | jq -r '.repository_url // "Failed"')"
echo "Enterprise repo: $(echo "$ENTERPRISE_RESPONSE" | jq -r '.repository_url // "Failed"')"
echo ""
echo "✨ Test complete!"