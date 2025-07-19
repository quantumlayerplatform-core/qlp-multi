#!/bin/bash

# Test Enterprise Capsule Generation
echo "🚀 Testing Enterprise Capsule Generation"
echo "========================================"

# Test endpoint
API_URL="http://localhost:8000/execute/enterprise"

# Test case: Create a Python web API with FastAPI
echo -e "\n📝 Test Case: Python FastAPI Web Service"
echo "----------------------------------------"

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "description": "Create a RESTful API service for managing a book library with FastAPI",
    "requirements": "The API should have endpoints for CRUD operations on books (title, author, ISBN, publication year). Include proper error handling, input validation, and OpenAPI documentation. Add a simple in-memory database for storage.",
    "tier_override": "T2"
  }' | jq '.'

echo -e "\n\n✅ Workflow started! Use the workflow_id to check status:"
echo "curl http://localhost:8000/status/{workflow_id}"

echo -e "\n📊 To view the capsule when ready:"
echo "curl http://localhost:8000/capsule/{workflow_id}"

echo -e "\n💡 Enterprise features included:"
echo "  - Comprehensive README.md with badges and examples"
echo "  - API documentation (OpenAPI/Swagger)"
echo "  - Architecture documentation"
echo "  - Docker support with multi-stage builds"
echo "  - CI/CD pipelines (GitHub Actions, GitLab CI)"
echo "  - Testing configurations (pytest, coverage)"
echo "  - Linting configurations (.flake8, .eslintrc)"
echo "  - Security best practices"
echo "  - Development and deployment guides"
echo "  - Contributing guidelines and Code of Conduct"