#!/bin/bash

# Test Enterprise Capsule Generation with Multiple Languages
echo "🌍 Testing Enterprise Capsule Generation - Multi-Language Support"
echo "================================================================"

API_URL="http://localhost:8000/execute/enterprise"

# Test 1: Go Microservice
echo -e "\n📝 Test 1: Go Microservice with gRPC"
echo "------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "description": "Build a Go microservice for user authentication with gRPC",
    "requirements": "Create a gRPC service in Go that handles user registration, login, and JWT token generation. Include password hashing with bcrypt, token validation middleware, and proper error handling. Add protocol buffer definitions.",
    "tier_override": "T2"
  }' | jq '.'

sleep 2

# Test 2: TypeScript React App
echo -e "\n\n📝 Test 2: TypeScript React Application"
echo "---------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "description": "Create a modern React application with TypeScript for task management",
    "requirements": "Build a task management app with React and TypeScript. Features: create/edit/delete tasks, mark as complete, filter by status, local storage persistence. Use functional components with hooks, proper type definitions, and responsive design.",
    "tier_override": "T2"
  }' | jq '.'

sleep 2

# Test 3: Rust CLI Tool
echo -e "\n\n📝 Test 3: Rust Command-Line Tool"
echo "---------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "description": "Develop a Rust CLI tool for file encryption",
    "requirements": "Create a command-line tool in Rust that can encrypt and decrypt files using AES-256. Support password-based encryption, progress bars for large files, and multiple file selection. Include proper error handling and help documentation.",
    "tier_override": "T2"
  }' | jq '.'

sleep 2

# Test 4: Java Spring Boot API
echo -e "\n\n📝 Test 4: Java Spring Boot REST API"
echo "------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "description": "Build a Spring Boot REST API for inventory management",
    "requirements": "Create a Spring Boot application with REST endpoints for managing product inventory. Include JPA entities for products and categories, pagination support, search functionality, and Swagger documentation. Use H2 for development database.",
    "tier_override": "T2"
  }' | jq '.'

echo -e "\n\n🎯 All tests submitted!"
echo "========================"
echo -e "\nEach request will generate an enterprise-grade capsule with:"
echo "  ✓ Language-specific project structure"
echo "  ✓ Appropriate build files (go.mod, package.json, Cargo.toml, pom.xml)"
echo "  ✓ Language-specific CI/CD pipelines"
echo "  ✓ Docker support optimized for each language"
echo "  ✓ Comprehensive documentation"
echo "  ✓ Testing frameworks specific to each language"
echo "  ✓ Linting and formatting tools"
echo -e "\n💡 The AI will automatically detect the language and apply best practices!"