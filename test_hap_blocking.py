#!/usr/bin/env python3
"""
Test HAP blocking in execute endpoint
"""

import requests
import time

print("Testing HAP Blocking Integration")
print("=" * 50)

# Wait for service to be ready
time.sleep(5)

# Test 1: Clean request (should work)
print("\n1. Testing clean request...")
response = requests.post(
    "http://localhost:8000/execute",
    json={
        "tenant_id": "test",
        "user_id": "test_user",
        "description": "Create a function to sort a list"
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 2: Medium severity (should work but log)
print("\n2. Testing medium severity (insults)...")
response = requests.post(
    "http://localhost:8000/execute",
    json={
        "tenant_id": "test",
        "user_id": "test_user",
        "description": "Fix this stupid idiot code"
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 3: High severity (should be blocked)
print("\n3. Testing high severity (threat)...")
response = requests.post(
    "http://localhost:8000/execute",
    json={
        "tenant_id": "test",
        "user_id": "test_user",
        "description": "I will hurt anyone who uses tabs instead of spaces"
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 400:
    print("\n✅ SUCCESS: High severity content was blocked!")
else:
    print("\n❌ FAILURE: High severity content was NOT blocked!")
    print("\nPossible issues:")
    print("1. HAP integration code not loaded")
    print("2. Check docker logs: docker logs qlp-orchestrator | grep -i hap")
    print("3. Verify main.py has HAP check in execute_request function")

# Test 4: Direct HAP API to confirm it's working
print("\n4. Testing HAP API directly...")
response = requests.post(
    "http://localhost:8000/api/v2/hap/check",
    json={
        "content": "I will hurt anyone who uses tabs instead of spaces",
        "context": "user_request"
    }
)
print(f"HAP API Response: {response.json()}")