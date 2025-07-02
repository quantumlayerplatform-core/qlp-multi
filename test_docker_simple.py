#!/usr/bin/env python3
"""Simple test for Docker environment"""

import requests
import json
import time

def test_services():
    """Test all services are running"""
    services = [
        ("Orchestrator", "http://orchestrator:8000/health"),
        ("Agent Factory", "http://agent-factory:8001/health"),
        ("Validation Mesh", "http://validation-mesh:8002/health"),
        ("Vector Memory", "http://vector-memory:8003/health"),
        ("Execution Sandbox", "http://execution-sandbox:8004/health"),
    ]
    
    print("🐳 Testing Docker services...")
    print("=" * 60)
    
    all_healthy = True
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: Healthy")
            else:
                print(f"❌ {name}: Unhealthy (status: {response.status_code})")
                all_healthy = False
        except Exception as e:
            print(f"❌ {name}: Failed ({str(e)})")
            all_healthy = False
    
    print("=" * 60)
    
    if all_healthy:
        print("✅ All services are healthy!")
    else:
        print("❌ Some services are not healthy")
    
    return all_healthy

def test_capsule_generation():
    """Test capsule generation"""
    print("\n📦 Testing capsule generation...")
    print("=" * 60)
    
    request_data = {
        "request_id": "docker-test-001",
        "tenant_id": "docker-tenant",
        "user_id": "docker-user",
        "project_name": "Docker Test Project",
        "description": "A simple hello world function in Python",
        "requirements": [
            "Create a function that prints 'Hello from Docker!'",
            "Include a simple test"
        ],
        "tech_stack": ["Python"],
        "target_environment": "docker"
    }
    
    try:
        response = requests.post(
            "http://orchestrator:8000/generate/capsule",
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Capsule generated successfully!")
            print(f"   Request ID: {result.get('request_id')}")
            print(f"   Files: {result.get('file_count', 0)}")
            print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
            return True
        else:
            print(f"❌ Generation failed (status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🌟 QUANTUM LAYER PLATFORM - DOCKER INTEGRATION TEST")
    print("=" * 60)
    
    # Test services
    services_ok = test_services()
    
    if services_ok:
        # Test capsule generation
        generation_ok = test_capsule_generation()
        
        if generation_ok:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Generation test failed")
    else:
        print("\n⚠️  Skipping generation test due to unhealthy services")

if __name__ == "__main__":
    main()