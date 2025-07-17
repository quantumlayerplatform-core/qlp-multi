#!/usr/bin/env python3
"""
Test script to check validation results in capsule
"""

import requests
import json
import time

# Production URL via LoadBalancer
base_url = "http://85.210.81.162"

# Simple request
request_data = {
    "description": "Create a Python function that checks if a number is prime",
    "tenant_id": "test-tenant",
    "user_id": "test-user"
}

print("\n🚀 Testing Validation Results")
print(f"URL: {base_url}")

# Submit request
print("\n📤 Submitting request...")
response = requests.post(f"{base_url}/execute", json=request_data)

if response.status_code != 200:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)
    exit(1)

result = response.json()
workflow_id = result.get('workflow_id')
print(f"✅ Workflow ID: {workflow_id}")

# Wait for completion
print("\n⏳ Waiting for completion...")
for i in range(30):
    status_response = requests.get(f"{base_url}/workflow/status/{workflow_id}")
    if status_response.status_code == 200:
        status = status_response.json()
        if status.get('status') == 'COMPLETED':
            print("✅ Workflow completed!")
            
            # Get the capsule
            if status.get('result') and status['result'].get('capsule_id'):
                capsule_id = status['result']['capsule_id']
                print(f"\n📦 Capsule ID: {capsule_id}")
                
                # Get capsule details
                capsule_response = requests.get(f"{base_url}/capsule/{capsule_id}")
                if capsule_response.status_code == 200:
                    capsule = capsule_response.json()
                    
                    # Check validation report
                    validation_report = capsule.get('validation_report')
                    if validation_report:
                        print("\n✅ VALIDATION REPORT FOUND!")
                        print(json.dumps(validation_report, indent=2))
                        
                        # Check if validation passed
                        if validation_report.get('passed'):
                            print("\n✔️  Validation PASSED")
                        else:
                            print("\n❌ Validation FAILED")
                    else:
                        print("\n⚠️  No validation report in capsule")
                        
                    # Check for validation in task results
                    if status.get('result') and status['result'].get('tasks'):
                        print("\n🔍 Checking task validation results...")
                        for task in status['result']['tasks']:
                            if task.get('validation'):
                                print(f"\nTask {task.get('task_id')} validation:")
                                print(json.dumps(task['validation'], indent=2))
                else:
                    print(f"\n❌ Failed to get capsule: {capsule_response.status_code}")
            break
        elif status.get('status') == 'FAILED':
            print("❌ Workflow failed!")
            print(json.dumps(status, indent=2))
            break
    time.sleep(5)
else:
    print("\n⏱️  Timeout waiting for completion")