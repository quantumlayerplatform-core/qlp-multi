#!/usr/bin/env python3
"""
Test current API functionality
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("🔍 Testing Current API Endpoints\n")
    
    # Test health endpoints
    endpoints = [
        ("GET", "/health", None),
        ("GET", "/api/v2/health", None),
        ("GET", "/openapi.json", None),
        ("GET", "/docs", None),
    ]
    
    for method, endpoint, data in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url, json=data)
            
            print(f"✅ {method} {endpoint}: {response.status_code}")
            
            if endpoint.endswith(".json") or "api" in endpoint:
                try:
                    json_data = response.json()
                    if "version" in str(json_data):
                        print(f"   Version info found")
                    if "success" in json_data:
                        print(f"   Success field: {json_data['success']}")
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ {method} {endpoint}: {e}")
    
    # Test API versioning
    print("\n📊 API Version Information:")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        openapi = response.json()
        print(f"   API Title: {openapi['info']['title']}")
        print(f"   API Version: {openapi['info']['version']}")
        
        # Count v2 endpoints
        v2_endpoints = [path for path in openapi['paths'] if '/api/v2' in path]
        print(f"   V2 Endpoints: {len(v2_endpoints)}")
        for endpoint in v2_endpoints[:5]:
            print(f"      - {endpoint}")
            
    except Exception as e:
        print(f"   Error getting version info: {e}")
    
    # Test existing capsule endpoints
    print("\n🧪 Testing Capsule Endpoints:")
    test_data = {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "description": "Test project"
    }
    
    capsule_endpoints = [
        ("/execute", test_data),
        ("/generate/capsule", test_data),
    ]
    
    for endpoint, data in capsule_endpoints:
        try:
            response = requests.post(f"{BASE_URL}{endpoint}", json=data)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "workflow_id" in result:
                    print(f"      Workflow ID: {result['workflow_id']}")
                elif "capsule_id" in result:
                    print(f"      Capsule ID: {result['capsule_id']}")
        except Exception as e:
            print(f"   {endpoint}: Error - {e}")

if __name__ == "__main__":
    test_endpoints()