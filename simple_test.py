#!/usr/bin/env python3
"""
Simple test using your actual external services
No port forwarding needed!
"""

import asyncio
import httpx

async def test_with_external_services():
    print("🚀 Testing QLP with External Services")
    print("=" * 50)
    
    # Your external orchestrator IP
    orchestrator_url = "http://85.210.81.162"
    
    print(f"🎯 Testing Orchestrator: {orchestrator_url}")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Test orchestrator health
            print("1️⃣ Checking orchestrator health...")
            health_response = await client.get(f"{orchestrator_url}/health")
            print(f"   Health Status: {health_response.status_code}")
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"   Service: {health_data.get('service', 'unknown')}")
                print(f"   Status: {health_data.get('status', 'unknown')}")
                
            # 2. Test the problematic decompose endpoint
            print("\n2️⃣ Testing decompose endpoint (this should fail)...")
            decompose_response = await client.post(
                f"{orchestrator_url}/decompose/unified-optimization",
                json={
                    "description": "Create a simple REST API",
                    "tenant_id": "test", 
                    "user_id": "debug",
                    "similar_requests": []  # Empty - this causes the error
                }
            )
            
            print(f"   Decompose Status: {decompose_response.status_code}")
            
            if decompose_response.status_code == 200:
                print("   ✅ Decompose works! (Unexpected)")
                result = decompose_response.json()
                print(f"   Tasks created: {len(result.get('tasks', []))}")
            else:
                error_text = decompose_response.text
                print(f"   ❌ Decompose failed: {error_text[:200]}...")
                
                if "list index out of range" in error_text.lower():
                    print("   🎯 CONFIRMED: This is the exact error your worker hits!")
                    print("   💡 Solution: Fix the decompose endpoint to handle empty similar_requests")
                elif "not found" in error_text.lower() or decompose_response.status_code == 404:
                    print("   📝 The /decompose/unified-optimization endpoint doesn't exist!")
                    print("   💡 Solution: Add the decompose endpoints to your orchestrator")
                
            # 3. Test if basic decompose endpoint exists
            print("\n3️⃣ Testing basic decompose endpoint...")
            basic_response = await client.post(
                f"{orchestrator_url}/decompose/basic",
                json={
                    "description": "Create a simple REST API"
                }
            )
            
            print(f"   Basic Decompose Status: {basic_response.status_code}")
            
            if basic_response.status_code == 404:
                print("   📝 Basic decompose endpoint also doesn't exist")
                print("   💡 Need to add both endpoints to your orchestrator")
            elif basic_response.status_code == 200:
                print("   ✅ Basic decompose works!")
                
            # 4. Check what endpoints exist
            print("\n4️⃣ Checking available endpoints...")
            docs_response = await client.get(f"{orchestrator_url}/docs")
            if docs_response.status_code == 200:
                print("   📚 API docs available at /docs")
            else:
                print("   📝 No API docs found")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    print("\n🎯 DIAGNOSIS:")
    print("The issue is likely one of:")
    print("1. The /decompose/unified-optimization endpoint doesn't exist")
    print("2. The endpoint exists but doesn't handle empty similar_requests")
    print("3. Vector DB is empty, so similar_requests is always empty")
    
    print("\n💡 NEXT STEPS:")
    print("1. Add the decompose endpoints to your orchestrator (from the artifacts)")
    print("2. Vector DB is internal-only, so populate it from within the cluster")
    print("3. Update worker to handle empty responses gracefully")

if __name__ == "__main__":
    asyncio.run(test_with_external_services())
