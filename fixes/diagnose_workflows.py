#!/usr/bin/env python3
"""
Quick diagnostic to check the workflow differences
"""
import requests
import json

print("=== Checking Workflow Differences ===\n")

# Test 1: Check if enterprise endpoint exists
print("1. Checking endpoint availability:")
endpoints = [
    ("Regular Execute", "http://localhost:8000/execute"),
    ("Enterprise Execute", "http://localhost:8000/execute/enterprise"),
    ("V2 Execute", "http://localhost:8000/v2/execute"),
    ("Enterprise Generate", "http://localhost:8000/api/enterprise/generate")
]

for name, url in endpoints:
    try:
        # Just check if endpoint exists with OPTIONS request
        response = requests.options(url, timeout=2)
        print(f"   {name}: {response.status_code} {'✓' if response.status_code < 500 else '✗'}")
    except Exception as e:
        print(f"   {name}: Failed - {type(e).__name__}")

print("\n2. Recent workflow analysis:")
# This would require access to Temporal directly, but we can infer from our tests

print("""
   Regular workflow (/execute):
   - Status: WORKING ✓
   - Duration: ~30-60 seconds
   - Creates capsule successfully
   
   Enterprise workflow (/execute/enterprise):
   - Status: FAILING ✗
   - Issue: Temporal sandbox restriction (os.path.abspath)
   - Never reaches capsule generation stage
""")

print("\n3. Root cause:")
print("""
   The enterprise_worker.py imports modules that use os.path.abspath at the module level.
   This is forbidden in Temporal's workflow sandbox for security reasons.
   
   The regular worker (worker_production_enhanced.py) likely avoids these imports
   or handles them differently.
""")

print("\n4. Solution paths:")
print("""
   a) Use the regular workflow with enterprise features:
      - Add 'use_enterprise_capsule': true to the request
      - Modify the regular workflow to check this flag
      
   b) Fix the enterprise worker:
      - Remove all module-level os.path usage
      - Move imports inside functions
      - Use Temporal's pass-through imports
      
   c) Create a hybrid approach:
      - Use regular workflow for execution
      - Post-process with enterprise capsule generator
""")
