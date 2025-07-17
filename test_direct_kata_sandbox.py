#!/usr/bin/env python3
"""
Direct test of sandbox service with Kata/gVisor runtime
"""

import requests
import json

# Sandbox service URL (requires port-forward)
sandbox_url = "http://localhost:8004"

# Test code
test_code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Test the function
print(f"Factorial of 5: {factorial(5)}")
print(f"Factorial of 10: {factorial(10)}")
print("Runtime test successful!")
"""

print("🧑‍🔬 Testing Sandbox with Different Runtimes\n")

# Test with Docker runtime
print("1️⃣  Testing with Docker runtime...")
try:
    response = requests.post(
        f"{sandbox_url}/execute",
        json={
            "code": test_code,
            "language": "python",
            "runtime": "docker"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Success!")
        print(f"   Runtime: {result.get('runtime', 'docker')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Duration: {result.get('duration_ms')}ms")
        if result.get('output'):
            print(f"   Output:\n{result['output'].strip()}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("   Make sure to run: kubectl port-forward svc/execution-sandbox-svc 8004:8004 -n qlp-production")

# Test with Kata/gVisor runtime
print("\n2️⃣  Testing with Kata/gVisor runtime...")
try:
    response = requests.post(
        f"{sandbox_url}/execute",
        json={
            "code": test_code,
            "language": "python",
            "runtime": "kata"  # Will use gVisor as fallback
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Success!")
        print(f"   Runtime: {result.get('runtime', 'unknown')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Duration: {result.get('duration_ms')}ms")
        print(f"   Execution ID: {result.get('execution_id')}")
        if result.get('output'):
            print(f"   Output:\n{result['output'].strip()}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check sandbox health
print("\n3️⃣  Checking sandbox health...")
try:
    health_response = requests.get(f"{sandbox_url}/health")
    if health_response.status_code == 200:
        health = health_response.json()
        print(f"   ✅ Service: {health.get('service')}")
        print(f"   Status: {health.get('status')}")
        print(f"   Docker: {health.get('docker')}")
except Exception as e:
    print(f"   ❌ Error: {e}")