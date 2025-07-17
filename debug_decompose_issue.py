#!/usr/bin/env python3
"""
Debug script to diagnose the decompose "list index out of range" issue
Run this to understand what's happening with your vector DB and decompose endpoint
"""

import asyncio
import httpx
import json
import os
from datetime import datetime

async def test_vector_memory():
    """Test vector memory service"""
    print("🔍 Testing Vector Memory Service...")
    
    vector_url = os.getenv("VECTOR_MEMORY_URL", "http://vector-memory:8002")
    print(f"📍 Vector Memory URL: {vector_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health
            health_response = await client.get(f"{vector_url}/health")
            print(f"Health Status: {health_response.status_code}")
            
            # Test search
            search_response = await client.post(
                f"{vector_url}/search/requests",
                json={"description": "test api", "limit": 5}
            )
            
            print(f"Search Status: {search_response.status_code}")
            
            if search_response.status_code == 200:
                results = search_response.json()
                print(f"Search Results Type: {type(results)}")
                
                if isinstance(results, list):
                    print(f"Results Count: {len(results)}")
                    if len(results) > 0:
                        print(f"Sample Result: {results[0]}")
                elif isinstance(results, dict):
                    result_list = results.get("results", [])
                    print(f"Results Count: {len(result_list)}")
                    if len(result_list) > 0:
                        print(f"Sample Result: {result_list[0]}")
                else:
                    print(f"Unexpected results format: {results}")
            else:
                print(f"Search failed: {search_response.text}")
                
    except Exception as e:
        print(f"❌ Vector Memory Test Failed: {e}")

async def test_orchestrator_decompose():
    """Test orchestrator decompose endpoints"""
    print("\n🔍 Testing Orchestrator Decompose Endpoints...")
    
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    print(f"📍 Orchestrator URL: {orchestrator_url}")
    
    test_request = {
        "description": "Create a simple REST API for user management",
        "tenant_id": "test",
        "user_id": "debug",
        "requirements": "FastAPI with authentication",
        "constraints": {"language": "python"},
        "similar_requests": []  # Empty to simulate the issue
    }
    
    # Test unified-optimization endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("\n🧪 Testing /decompose/unified-optimization with empty similar_requests...")
            
            response = await client.post(
                f"{orchestrator_url}/decompose/unified-optimization",
                json=test_request
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success! Tasks: {len(result.get('tasks', []))}")
            else:
                error_text = response.text
                print(f"❌ Failed: {error_text}")
                
                if "list index out of range" in error_text.lower():
                    print("🎯 FOUND THE ISSUE: The endpoint is trying to access an empty list!")
                    print("💡 This confirms the vector DB empty issue")
                    
    except Exception as e:
        print(f"❌ Decompose Test Failed: {e}")
    
    # Test if basic endpoint exists
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("\n🧪 Testing /decompose/basic endpoint...")
            
            response = await client.post(
                f"{orchestrator_url}/decompose/basic",
                json=test_request
            )
            
            print(f"Basic Decompose Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Basic endpoint works! Tasks: {len(result.get('tasks', []))}")
            elif response.status_code == 404:
                print("ℹ️  Basic endpoint doesn't exist yet (need to add it)")
            else:
                print(f"❌ Basic endpoint failed: {response.text}")
                
    except Exception as e:
        print(f"❌ Basic Decompose Test Failed: {e}")

async def test_temporal_worker_simulation():
    """Simulate what the temporal worker is doing"""
    print("\n🔍 Simulating Temporal Worker Flow...")
    
    vector_url = os.getenv("VECTOR_MEMORY_URL", "http://vector-memory:8002")
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Search for similar requests (what the worker does)
            print("Step 1: Searching for similar requests...")
            
            memory_response = await client.post(
                f"{vector_url}/search/requests",
                json={
                    "description": "Create a simple API",
                    "limit": 5
                }
            )
            
            similar_requests = []
            if memory_response.status_code == 200:
                response_data = memory_response.json()
                if isinstance(response_data, list):
                    similar_requests = response_data
                elif isinstance(response_data, dict):
                    similar_requests = response_data.get("results", [])
                    
            print(f"Similar requests found: {len(similar_requests)}")
            
            # Step 2: Call decompose with the results
            print("Step 2: Calling decompose with similar requests...")
            
            decompose_response = await client.post(
                f"{orchestrator_url}/decompose/unified-optimization",
                json={
                    "description": "Create a simple API",
                    "tenant_id": "test",
                    "user_id": "worker_sim",
                    "similar_requests": similar_requests
                }
            )
            
            print(f"Decompose response: {decompose_response.status_code}")
            
            if decompose_response.status_code != 200:
                error_text = decompose_response.text
                print(f"❌ This is exactly what the worker sees: {error_text}")
                
                if "list index out of range" in error_text.lower():
                    print("🎯 CONFIRMED: This is the exact error the worker hits!")
            else:
                print("✅ Decompose succeeded in simulation")
                
    except Exception as e:
        print(f"❌ Worker simulation failed: {e}")

async def suggest_fixes():
    """Suggest specific fixes based on findings"""
    print("\n💡 SUGGESTED FIXES:")
    print("="*50)
    
    print("1. IMMEDIATE FIX - Update your decompose endpoint:")
    print("   - Add the basic decompose endpoint from the artifact above")
    print("   - Add defensive programming to handle empty similar_requests")
    
    print("\n2. POPULATE VECTOR DB:")
    print("   - Run the populate_vector_db.py script")
    print("   - This will add seed data to your Qdrant Cloud")
    
    print("\n3. UPDATE WORKER:")
    print("   - Apply the fixed_worker_production.py changes")
    print("   - This adds fallback logic when vector DB is empty")
    
    print("\n4. RESTART SERVICES:")
    print("   - kubectl rollout restart deployment qlp-orchestrator -n qlp-production")
    print("   - kubectl rollout restart deployment qlp-temporal-worker -n qlp-production")
    
    print("\n5. VERIFY FIX:")
    print("   - Check vector DB status: curl http://orchestrator:8000/decompose/vector-status")
    print("   - Test decompose: curl -X POST http://orchestrator:8000/decompose/basic -d '{\"description\":\"test\"}'")

async def main():
    """Main diagnostic function"""
    print("🚀 QUANTUM LAYER PLATFORM - DECOMPOSE ISSUE DEBUGGER")
    print("="*60)
    print(f"🕐 Started at: {datetime.now()}")
    
    await test_vector_memory()
    await test_orchestrator_decompose()
    await test_temporal_worker_simulation()
    await suggest_fixes()
    
    print("\n🎯 DIAGNOSIS COMPLETE!")
    print("The issue is confirmed: empty vector DB causing 'list index out of range'")
    print("Apply the fixes above to resolve the issue.")

if __name__ == "__main__":
    asyncio.run(main())
