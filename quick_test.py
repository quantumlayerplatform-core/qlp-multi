#!/usr/bin/env python3
"""
Quick test to check our services and vector DB status
"""

import asyncio
import httpx
import os

async def quick_test():
    print("🔍 Quick QLP Services Test")
    print("=" * 40)
    
    # Use the external LoadBalancer IP
    orchestrator_url = "http://85.210.81.162"  # Your external IP
    
    # For vector-memory, we'll need port-forward or try internal service
    vector_urls_to_try = [
        "http://localhost:8003",  # Port forwarded
        "http://vector-memory-svc.qlp-production.svc.cluster.local:8003",  # Direct k8s
    ]
    
    print(f"🎯 Testing Orchestrator at: {orchestrator_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test orchestrator health
            response = await client.get(f"{orchestrator_url}/health")
            print(f"Orchestrator Health: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Orchestrator Status: {data}")
            
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
    
    # Test vector memory
    print(f"\n🎯 Testing Vector Memory...")
    vector_working_url = None
    
    for vector_url in vector_urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{vector_url}/health")
                if response.status_code == 200:
                    print(f"✅ Vector Memory working at: {vector_url}")
                    vector_working_url = vector_url
                    break
                else:
                    print(f"⚠️  Vector Memory at {vector_url}: {response.status_code}")
        except Exception as e:
            print(f"❌ Vector Memory at {vector_url}: {e}")
    
    if vector_working_url:
        # Test if vector DB has data
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_response = await client.post(
                    f"{vector_working_url}/search/requests",
                    json={"description": "test", "limit": 1}
                )
                
                if search_response.status_code == 200:
                    results = search_response.json()
                    result_list = results if isinstance(results, list) else results.get("results", [])
                    print(f"Vector DB Data Check: {len(result_list)} results found")
                    
                    if len(result_list) == 0:
                        print("🎯 CONFIRMED: Vector DB is empty! This is causing the 'list index out of range' error.")
                    else:
                        print(f"Vector DB has {len(result_list)} entries")
                else:
                    print(f"Vector DB search failed: {search_response.status_code}")
                    
        except Exception as e:
            print(f"❌ Vector DB data check failed: {e}")
    
    # Now test the decompose endpoint with empty similar_requests
    print(f"\n🧪 Testing Decompose Endpoint...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{orchestrator_url}/decompose/unified-optimization",
                json={
                    "description": "Create a simple REST API",
                    "tenant_id": "test",
                    "user_id": "debug",
                    "similar_requests": []  # This is what's causing the issue
                }
            )
            
            print(f"Decompose Status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                print(f"Decompose Error: {error_text}")
                
                if "list index out of range" in error_text.lower():
                    print("🎯 FOUND THE EXACT ISSUE!")
                    print("The decompose endpoint is trying to access similar_requests[0] on an empty list")
                    
    except Exception as e:
        print(f"❌ Decompose test failed: {e}")

if __name__ == "__main__":
    asyncio.run(quick_test())
