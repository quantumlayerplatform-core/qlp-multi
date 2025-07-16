#!/bin/bash

# Test enterprise workflow with GitHub push enabled

curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a production-ready REST API service for user management with: User registration, login, profile management; JWT authentication with refresh tokens; Role-based access control (admin, user roles); PostgreSQL database with proper migrations; Input validation and error handling; Unit tests with >80% coverage; API documentation (OpenAPI/Swagger); Docker configuration for deployment; Security best practices including threat modeling",
    "requirements": "Production-ready code with proper error handling; Comprehensive test coverage (>80%); Security-first design with threat modeling; Performance optimized for 1000+ concurrent users; Proper logging and monitoring setup",
    "tier_override": "T2",
    "user_id": "test-user-github",
    "tenant_id": "enterprise-test",
    "metadata": {
      "push_to_github": true,
      "github_repo_name": "user-management-api",
      "github_private": false,
      "github_enterprise": true
    }
  }'