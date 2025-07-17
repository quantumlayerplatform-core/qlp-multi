#!/usr/bin/env python3

import requests
import time
import json

base_url = "http://85.210.81.162"

# Submit request
print("Submitting request...")
resp = requests.post(f"{base_url}/execute", json={
    "description": "Create a function to add two numbers",
    "tenant_id": "test",
    "user_id": "test"
})

workflow_id = resp.json()['workflow_id']
print(f"Workflow ID: {workflow_id}")

# Wait for completion
for i in range(30):
    resp = requests.get(f"{base_url}/workflow/status/{workflow_id}")
    status = resp.json()
    
    if status['status'] == 'COMPLETED':
        print("\nWorkflow completed!")
        
        # Pretty print the result
        if status.get('result'):
            print("\nResult:")
            print(json.dumps(status['result'], indent=2))
            
            # Check for validation in tasks
            if status['result'].get('tasks'):
                print("\nChecking for validation...")
                for task in status['result']['tasks']:
                    if task.get('validation'):
                        print(f"\n✅ VALIDATION FOUND for task {task['task_id']}!")
                        print(json.dumps(task['validation'], indent=2))
                    else:
                        print(f"\n❌ No validation for task {task['task_id']}")
        break
    
    print(f"Status: {status['status']}...")
    time.sleep(5)