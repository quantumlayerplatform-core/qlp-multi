#!/bin/bash

# Compare Standard vs Enterprise Capsule Generation
echo "⚖️  Comparing Standard vs Enterprise Capsule Generation"
echo "====================================================="

# Simple factorial function for comparison
DESCRIPTION="Create a factorial function that calculates n!"
REQUIREMENTS="The function should handle edge cases like negative numbers and non-integers. Include proper error handling."

echo -e "\n📦 Test 1: Standard Capsule (using /execute)"
echo "--------------------------------------------"
STANDARD_RESPONSE=$(curl -s -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"test-tenant\",
    \"user_id\": \"test-user\",
    \"description\": \"$DESCRIPTION\",
    \"requirements\": \"$REQUIREMENTS\"
  }")

STANDARD_WORKFLOW_ID=$(echo "$STANDARD_RESPONSE" | jq -r '.workflow_id')
echo "Standard Workflow ID: $STANDARD_WORKFLOW_ID"

echo -e "\n🏢 Test 2: Enterprise Capsule (using /execute/enterprise)"
echo "---------------------------------------------------------"
ENTERPRISE_RESPONSE=$(curl -s -X POST "http://localhost:8000/execute/enterprise" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"test-tenant\",
    \"user_id\": \"test-user\",
    \"description\": \"$DESCRIPTION\",
    \"requirements\": \"$REQUIREMENTS\"
  }")

ENTERPRISE_WORKFLOW_ID=$(echo "$ENTERPRISE_RESPONSE" | jq -r '.workflow_id')
echo "Enterprise Workflow ID: $ENTERPRISE_WORKFLOW_ID"
echo -e "\nEnterprise Features:"
echo "$ENTERPRISE_RESPONSE" | jq '.features'

echo -e "\n\n📊 Expected Differences:"
echo "========================"
echo -e "\n🔹 Standard Capsule:"
echo "  - Single file with factorial function"
echo "  - Basic test file"
echo "  - Minimal documentation"
echo ""
echo -e "🔸 Enterprise Capsule:"
echo "  - Complete project structure:"
echo "    ├── src/"
echo "    │   └── factorial.py"
echo "    ├── tests/"
echo "    │   └── test_factorial.py"
echo "    ├── docs/"
echo "    │   ├── README.md"
echo "    │   ├── ARCHITECTURE.md"
echo "    │   ├── DEVELOPMENT.md"
echo "    │   └── DEPLOYMENT.md"
echo "    ├── .github/"
echo "    │   └── workflows/"
echo "    │       └── main.yml"
echo "    ├── Dockerfile"
echo "    ├── docker-compose.yml"
echo "    ├── pyproject.toml"
echo "    ├── requirements.txt"
echo "    ├── .gitignore"
echo "    ├── .flake8"
echo "    ├── pytest.ini"
echo "    ├── LICENSE"
echo "    ├── CONTRIBUTING.md"
echo "    ├── CODE_OF_CONDUCT.md"
echo "    └── SECURITY.md"

echo -e "\n\n🔍 To check workflow status:"
echo "curl http://localhost:8000/status/$STANDARD_WORKFLOW_ID    # Standard"
echo "curl http://localhost:8000/status/$ENTERPRISE_WORKFLOW_ID  # Enterprise"

echo -e "\n📥 To download capsules when ready:"
echo "curl http://localhost:8000/capsule/$STANDARD_WORKFLOW_ID/download -o standard_capsule.zip"
echo "curl http://localhost:8000/capsule/$ENTERPRISE_WORKFLOW_ID/download -o enterprise_capsule.zip"