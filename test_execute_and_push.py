#!/usr/bin/env python3
"""
Test /execute endpoint and push to GitHub
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


async def test_execute_and_push():
    """Test creating a capsule with /execute and pushing to GitHub"""
    
    print("\n🚀 Testing /execute and GitHub Push")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Create a capsule using /execute
        print("\n1️⃣ Creating capsule with /execute...")
        
        request_data = {
            "tenant_id": "demo",
            "user_id": "developer",
            "description": "Create a Python web scraper that can extract product information from e-commerce websites. Include functions to parse HTML, extract prices, titles, and images, and save data to JSON format."
        }
        
        print(f"📝 Request: {request_data['description'][:100]}...")
        
        response = await client.post(
            f"{BASE_URL}/execute",
            json=request_data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to execute: {response.text}")
            return None
        
        result = response.json()
        print(f"✅ Execution successful!")
        print(f"   Workflow ID: {result.get('workflow_id')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        
        capsule_id = result.get('capsule_id')
        if not capsule_id:
            print("❌ No capsule_id returned")
            return None
        
        print(f"   Capsule ID: {capsule_id}")
        
        # Step 2: Get capsule details
        print("\n2️⃣ Retrieving capsule details...")
        
        response = await client.get(f"{BASE_URL}/api/capsules/{capsule_id}")
        
        if response.status_code == 200:
            capsule_data = response.json()
            print(f"✅ Capsule retrieved successfully!")
            print(f"   Name: {capsule_data.get('manifest', {}).get('name')}")
            print(f"   Language: {capsule_data.get('manifest', {}).get('language')}")
            print(f"   Files: {len(capsule_data.get('source_code', {}))}")
            print(f"   Tests: {len(capsule_data.get('tests', {}))}")
            
            # Show file names
            if capsule_data.get('source_code'):
                print("\n   📁 Source files:")
                for filename in capsule_data['source_code'].keys():
                    print(f"      - {filename}")
            
            if capsule_data.get('tests'):
                print("\n   🧪 Test files:")
                for filename in capsule_data['tests'].keys():
                    print(f"      - {filename}")
        else:
            print(f"❌ Failed to get capsule: {response.text}")
        
        # Step 3: Push to GitHub (multiple options)
        if GITHUB_TOKEN:
            print("\n3️⃣ Pushing to GitHub...")
            print("\nTesting different push methods:")
            
            # Method 1: Standard push with v2
            print("\n   A. Standard push (v2)...")
            repo_name = f"qlp-web-scraper-v2-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            push_request = {
                "capsule_id": capsule_id,
                "github_token": GITHUB_TOKEN,
                "repo_name": repo_name,
                "private": False
            }
            
            response = await client.post(
                f"{BASE_URL}/api/github/push/v2",
                json=push_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Pushed successfully!")
                print(f"      Repository: {result.get('repository_url')}")
                print(f"      Files: {result.get('files_created')}")
            else:
                print(f"   ❌ Failed: {response.text}")
            
            # Method 2: Enterprise push
            print("\n   B. Enterprise push...")
            enterprise_repo_name = f"qlp-web-scraper-enterprise-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            enterprise_request = {
                "capsule_id": capsule_id,
                "github_token": GITHUB_TOKEN,
                "repo_name": enterprise_repo_name,
                "use_enterprise_structure": True
            }
            
            response = await client.post(
                f"{BASE_URL}/api/github/push/enterprise",
                json=enterprise_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Enterprise push successful!")
                print(f"      Repository: {result.get('repository_url')}")
                print(f"      Files: {result.get('files_created')}")
            else:
                print(f"   ❌ Failed: {response.text}")
            
        else:
            print("\n⚠️  Skipping GitHub push - No GITHUB_TOKEN environment variable set")
            print("   To test GitHub push, set your token:")
            print("   export GITHUB_TOKEN=your_github_personal_access_token")
        
        return capsule_id


async def test_simple_example():
    """Test with a simple example"""
    
    print("\n\n🎯 Testing Simple Example")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Create a simple calculator
        print("\n📝 Creating a simple calculator...")
        
        request_data = {
            "tenant_id": "test",
            "user_id": "dev",
            "description": "Create a Python calculator with add, subtract, multiply, and divide functions"
        }
        
        response = await client.post(
            f"{BASE_URL}/execute",
            json=request_data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.text}")
            return
        
        result = response.json()
        capsule_id = result.get('capsule_id')
        print(f"✅ Created capsule: {capsule_id}")
        
        # Quick push to GitHub if token available
        if GITHUB_TOKEN and capsule_id:
            print("\n📤 Quick push to GitHub...")
            
            response = await client.post(
                f"{BASE_URL}/api/github/push/v2",
                json={
                    "capsule_id": capsule_id,
                    "github_token": GITHUB_TOKEN,
                    "repo_name": f"qlp-calculator-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Repository created: {result.get('repository_url')}")


async def main():
    """Run the tests"""
    
    print("\n🔧 Quantum Layer Platform - Execute and Push Test")
    print("=" * 60)
    
    # Check if services are running
    print("\n🔍 Checking services...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check orchestrator
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ Orchestrator is running")
            else:
                print("❌ Orchestrator health check failed")
                return
                
            # Check agent factory
            response = await client.get("http://localhost:8001/health")
            if response.status_code == 200:
                print("✅ Agent Factory is running")
            else:
                print("⚠️  Agent Factory not responding")
                
            # Check validation mesh
            response = await client.get("http://localhost:8002/health")
            if response.status_code == 200:
                print("✅ Validation Mesh is running")
            else:
                print("⚠️  Validation Mesh not responding")
                
    except Exception as e:
        print(f"❌ Cannot connect to services: {e}")
        print("\n📌 Please start the services with: ./start.sh")
        return
    
    # Check GitHub token
    if GITHUB_TOKEN:
        print(f"✅ GitHub token configured (length: {len(GITHUB_TOKEN)})")
    else:
        print("⚠️  No GitHub token found - push tests will be skipped")
    
    # Run tests
    capsule_id = await test_execute_and_push()
    await test_simple_example()
    
    print("\n\n✨ Testing complete!")
    
    if capsule_id:
        print(f"\n📌 You can also manually test the push with:")
        print(f"   curl -X POST {BASE_URL}/api/github/push/v2 \\")
        print(f"     -H 'Content-Type: application/json' \\")
        print(f"     -d '{{")
        print(f'       "capsule_id": "{capsule_id}",')
        print(f'       "github_token": "$GITHUB_TOKEN",')
        print(f'       "repo_name": "my-custom-repo-name"')
        print(f"     }}'")


if __name__ == "__main__":
    asyncio.run(main())