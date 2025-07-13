#!/usr/bin/env python3
"""
Quick test to verify cost tracking is working
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Submit a simple request
request_data = {
    "tenant_id": "test-tenant-cost-verify",
    "user_id": "test-user-123",
    "description": "Write a Python function to add two numbers"
}

print("Submitting request...")
response = requests.post(f"{BASE_URL}/execute", json=request_data)

if response.status_code == 200:
    result = response.json()
    workflow_id = result["workflow_id"]
    print(f"✅ Workflow submitted: {workflow_id}")
    
    # Wait for completion
    print("Waiting for completion...")
    for i in range(30):
        time.sleep(2)
        status_response = requests.get(f"{BASE_URL}/status/{workflow_id}")
        if status_response.status_code == 200:
            status = status_response.json()
            if status["status"] == "COMPLETED":
                print("✅ Workflow completed!")
                break
            elif status["status"] == "FAILED":
                print("❌ Workflow failed!")
                print(json.dumps(status, indent=2))
                break
    
    # Wait a bit for cost data to be persisted
    time.sleep(2)
    
    # Check database directly
    print(f"\nTo verify costs were saved, run:")
    print(f"docker exec qlp-postgres psql -U qlp_user -d qlp_db -c \"SELECT provider, model, input_tokens, output_tokens, total_cost_usd FROM llm_usage WHERE workflow_id = '{workflow_id}';\"")
else:
    print(f"❌ Failed to submit request: {response.status_code}")
    print(response.text)