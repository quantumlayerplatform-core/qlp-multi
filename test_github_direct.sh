#!/bin/bash

echo "🚀 Direct GitHub Push API Test"
echo "=============================="
echo ""

# Load environment
if [ -f ".env" ]; then
    source .env
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not found"
    exit 1
fi

echo "✅ GitHub token found"
echo ""

# Test the GitHub push endpoints directly
echo "1️⃣ Testing GitHub token validation..."

TOKEN_CHECK=$(curl -s "http://localhost:8000/api/github/check-token?token=$GITHUB_TOKEN")
echo "Token validation:"
echo "$TOKEN_CHECK" | jq '.'

VALID=$(echo "$TOKEN_CHECK" | jq -r '.valid // false')
if [ "$VALID" = "true" ]; then
    USERNAME=$(echo "$TOKEN_CHECK" | jq -r '.username')
    echo ""
    echo "✅ Token is valid for user: $USERNAME"
else
    echo ""
    echo "❌ Token validation failed"
    exit 1
fi

echo ""
echo "2️⃣ Testing repository creation via GitHub API..."

# Create a test repository directly using GitHub API to verify token works
REPO_NAME="qlp-direct-test-$(date +%Y%m%d%H%M%S)"

DIRECT_REPO=$(curl -s -X POST https://api.github.com/user/repos \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d "{
    \"name\": \"$REPO_NAME\",
    \"description\": \"Test repository created by QLP\",
    \"private\": false,
    \"auto_init\": false
  }")

REPO_URL=$(echo "$DIRECT_REPO" | jq -r '.html_url // empty')
if [ -n "$REPO_URL" ]; then
    echo "✅ Direct GitHub API works: $REPO_URL"
    
    # Clean up - delete the test repo
    REPO_FULL_NAME=$(echo "$DIRECT_REPO" | jq -r '.full_name')
    curl -s -X DELETE "https://api.github.com/repos/$REPO_FULL_NAME" \
      -H "Authorization: token $GITHUB_TOKEN" > /dev/null
    echo "🗑️  Cleaned up test repository"
else
    echo "❌ Direct GitHub API failed:"
    echo "$DIRECT_REPO" | jq '.'
fi

echo ""
echo "3️⃣ Testing QLP GitHub endpoints..."

# Test the atomic push endpoint with minimal data
echo "Testing atomic push endpoint..."

ATOMIC_TEST=$(curl -s -X POST http://localhost:8000/api/github/push/atomic \
  -H "Content-Type: application/json" \
  -d "{
    \"capsule_id\": \"test-capsule-id\",
    \"github_token\": \"$GITHUB_TOKEN\",
    \"repo_name\": \"qlp-atomic-test-$(date +%Y%m%d%H%M%S)\"
  }")

echo "Atomic push response:"
echo "$ATOMIC_TEST" | jq '.'

echo ""
echo "✨ Direct API test complete!"
echo ""
echo "📌 Summary:"
echo "   - GitHub token: $([ "$VALID" = "true" ] && echo "✅ Valid" || echo "❌ Invalid")"
echo "   - Direct GitHub API: $([ -n "$REPO_URL" ] && echo "✅ Working" || echo "❌ Failed")"
echo "   - QLP GitHub integration: Ready for testing with valid capsule"