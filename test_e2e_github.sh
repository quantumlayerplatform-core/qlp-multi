#!/bin/bash

# Test end-to-end flow: NLP → Code → Capsule → GitHub

echo "🚀 Testing end-to-end flow with GitHub integration..."
echo ""

# Test with the convenience endpoint
curl -X POST http://localhost:8000/generate/complete-with-github \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python REST API for managing a library of books. Include endpoints for CRUD operations on books (title, author, ISBN, year). Use FastAPI framework with SQLAlchemy for database operations. Include proper error handling and input validation.",
    "github_token": "${GITHUB_TOKEN}",
    "repo_name": "library-management-api",
    "private": false
  }' | jq '.'

echo ""
echo "✅ Test complete! Check the output above for the GitHub URL."