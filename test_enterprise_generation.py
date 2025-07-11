#!/usr/bin/env python3
"""
Test script for enterprise-grade capsule generation and GitHub push
"""
import asyncio
import os
import sys
import json
import httpx
from datetime import datetime

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:8000"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


async def test_enterprise_generation():
    """Test generating an enterprise-grade project"""
    
    print("\n🚀 Testing Enterprise-Grade Code Generation")
    print("=" * 60)
    
    # First, let's create a simple capsule using /execute
    print("\n1️⃣ Generating base code via /execute...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Generate base code
        request_data = {
            "tenant_id": "test-enterprise",
            "user_id": "developer",
            "description": "Create a Python REST API for a task management system with CRUD operations"
        }
        
        response = await client.post(
            f"{BASE_URL}/execute",
            json=request_data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to generate base code: {response.text}")
            return
        
        result = response.json()
        capsule_id = result.get("capsule_id")
        print(f"✅ Base capsule created: {capsule_id}")
        
        # Step 2: Transform to enterprise grade
        print("\n2️⃣ Transforming to enterprise-grade structure...")
        
        transform_request = {
            "enterprise_features": {
                "documentation": True,
                "testing": True,
                "ci_cd": True,
                "containerization": True,
                "monitoring": True,
                "security": True
            }
        }
        
        response = await client.post(
            f"{BASE_URL}/api/enterprise/transform/{capsule_id}",
            json=transform_request
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to transform: {response.text}")
            return
        
        enterprise_result = response.json()
        enterprise_capsule_id = enterprise_result.get("capsule_id")
        print(f"✅ Enterprise capsule created: {enterprise_capsule_id}")
        print(f"   Files count: {enterprise_result.get('files_count')}")
        print(f"   Structure version: {enterprise_result.get('structure_version')}")
        
        # Step 3: Get status
        print("\n3️⃣ Checking enterprise capsule status...")
        
        response = await client.get(
            f"{BASE_URL}/api/enterprise/status/{enterprise_capsule_id}"
        )
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Enterprise Status:")
            print(f"   - Is Enterprise: {status.get('is_enterprise_grade')}")
            print(f"   - File Types: {json.dumps(status.get('file_types'), indent=6)}")
            print(f"   - Enterprise Features: {json.dumps(status.get('enterprise_features'), indent=6)}")
        
        # Step 4: Push to GitHub with enterprise structure
        if GITHUB_TOKEN:
            print("\n4️⃣ Pushing to GitHub with enterprise structure...")
            
            github_request = {
                "capsule_id": enterprise_capsule_id,
                "github_token": GITHUB_TOKEN,
                "repo_name": f"qlp-task-api-enterprise-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "use_enterprise_structure": True
            }
            
            response = await client.post(
                f"{BASE_URL}/api/github/push/enterprise",
                json=github_request
            )
            
            if response.status_code == 200:
                github_result = response.json()
                print(f"✅ Pushed to GitHub: {github_result.get('repository_url')}")
                print(f"   Files created: {github_result.get('files_created')}")
            else:
                print(f"❌ Failed to push to GitHub: {response.text}")
        else:
            print("\n⚠️  Skipping GitHub push (no GITHUB_TOKEN set)")


async def test_direct_enterprise_generation():
    """Test direct enterprise generation in one step"""
    
    print("\n\n🚀 Testing Direct Enterprise Generation")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        request_data = {
            "description": "Create a Python microservice for user authentication with JWT tokens, password hashing, and role-based access control",
            "tenant_id": "test-direct",
            "user_id": "developer",
            "requirements": "Include user registration, login, token refresh, and user profile endpoints. Use FastAPI framework.",
            "enterprise_features": {
                "documentation": True,
                "testing": True,
                "ci_cd": True,
                "containerization": True,
                "monitoring": True,
                "security": True
            },
            "auto_push_github": bool(GITHUB_TOKEN),
            "github_token": GITHUB_TOKEN,
            "repo_name": f"qlp-auth-service-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "private_repo": False
        }
        
        print("\n📝 Generating enterprise project directly...")
        
        response = await client.post(
            f"{BASE_URL}/api/enterprise/generate",
            json=request_data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to generate: {response.text}")
            return
        
        result = response.json()
        print(f"✅ Enterprise project generated!")
        print(f"   Capsule ID: {result.get('capsule_id')}")
        print(f"   Workflow ID: {result.get('workflow_id')}")
        print(f"   Files count: {result.get('files_count')}")
        print(f"   GitHub URL: {result.get('github_url')}")
        print(f"   Structure version: {result.get('structure_version')}")


async def test_existing_capsule_enterprise_push():
    """Test pushing an existing capsule with enterprise structure"""
    
    print("\n\n🚀 Testing Existing Capsule Enterprise Push")
    print("=" * 60)
    
    # Use a known capsule ID (from the conversation context)
    capsule_id = "05590339-48ea-4702-b44a-8d67c406b0aa"
    
    if not GITHUB_TOKEN:
        print("⚠️  Skipping test (no GITHUB_TOKEN set)")
        return
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        print(f"\n📤 Pushing capsule {capsule_id} to GitHub with enterprise structure...")
        
        request_data = {
            "capsule_id": capsule_id,
            "github_token": GITHUB_TOKEN,
            "repo_name": f"qlp-shape-calculator-enterprise-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "use_enterprise_structure": True
        }
        
        response = await client.post(
            f"{BASE_URL}/api/github/push/enterprise",
            json=request_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully pushed with enterprise structure!")
            print(f"   Repository URL: {result.get('repository_url')}")
            print(f"   Files created: {result.get('files_created')}")
            print(f"   Clone URL: {result.get('clone_url')}")
        else:
            print(f"❌ Failed to push: {response.text}")


async def main():
    """Run all tests"""
    
    print("\n🔧 Enterprise-Grade Quantum Layer Platform Test Suite")
    print("=" * 60)
    
    # Check if services are running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ Orchestrator service is not running!")
                print("Please start the services with: ./start.sh")
                return
    except Exception as e:
        print(f"❌ Cannot connect to orchestrator: {e}")
        print("Please start the services with: ./start.sh")
        return
    
    # Run tests
    await test_enterprise_generation()
    await test_direct_enterprise_generation()
    await test_existing_capsule_enterprise_push()
    
    print("\n\n✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())