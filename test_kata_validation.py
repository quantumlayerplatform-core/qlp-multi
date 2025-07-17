#!/usr/bin/env python3
"""
Test script to verify Kata/gVisor validation is working
"""

import requests
import json
import time

# Production URL
base_url = "http://85.210.81.162"

# Test request
request_data = {
    "description": "Create a Python function that calculates factorial of a number",
    "tenant_id": "test-tenant",
    "user_id": "test-user"
}

print("\n🚀 Testing Validation with Secure Containers (Kata/gVisor)")
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
for i in range(60):  # Wait up to 5 minutes
    status_response = requests.get(f"{base_url}/workflow/status/{workflow_id}")
    if status_response.status_code == 200:
        status = status_response.json()
        
        if status.get('status') == 'COMPLETED':
            print("\n✅ Workflow completed!")
            
            # Get the full result
            full_response = requests.get(f"{base_url}/status/{workflow_id}")
            if full_response.status_code == 200:
                full_result = full_response.json()
                
                # Extract result from memo
                if full_result.get('memo') and full_result['memo'].get('result'):
                    workflow_result = json.loads(full_result['memo']['result'])
                    
                    # Check for validation with secure runtime
                    if workflow_result.get('outputs'):
                        print("\n🔍 Checking validation results...")
                        validation_found = False
                        
                        for output in workflow_result['outputs']:
                            if output.get('validation'):
                                validation = output['validation']
                                validation_found = True
                                
                                print(f"\n✅ VALIDATION FOUND for task {output['task_id']}")
                                print(f"   Status: {validation.get('overall_status')}")
                                print(f"   Confidence: {validation.get('confidence_score')}")
                                
                                # Check if validation metadata mentions runtime
                                metadata = validation.get('metadata', {})
                                if metadata:
                                    print(f"   Metadata: {json.dumps(metadata, indent=2)}")
                                
                                # Check individual checks
                                if validation.get('checks'):
                                    runtime_check = next((c for c in validation['checks'] 
                                                        if 'runtime' in c.get('name', '').lower()), None)
                                    if runtime_check:
                                        print(f"\n   🔒 Runtime Validation Check:")
                                        print(f"      Name: {runtime_check.get('name')}")
                                        print(f"      Status: {runtime_check.get('status')}")
                                        print(f"      Message: {runtime_check.get('message')}")
                        
                        if validation_found:
                            print("\n✅ VALIDATION WITH SECURE CONTAINERS IS WORKING!")
                            
                            # Check sandbox logs to confirm runtime used
                            print("\n🔍 Checking execution details...")
                            if workflow_result.get('metadata', {}).get('sandbox_validation'):
                                print("   Sandbox validation info:")
                                print(json.dumps(workflow_result['metadata']['sandbox_validation'], indent=2))
                        else:
                            print("\n⚠️  No validation found in results")
                else:
                    print("\n❌ Could not extract workflow result")
            break
        
        elif status.get('status') == 'FAILED':
            print("\n❌ Workflow failed!")
            print(json.dumps(status, indent=2))
            break
        else:
            print(f"\rStatus: {status.get('status', 'checking')}...", end='', flush=True)
    
    time.sleep(5)
else:
    print("\n⏱️  Timeout waiting for completion")

# Test direct sandbox execution with Kata
print("\n\n🧑‍🔬 Testing Direct Sandbox Execution with Kata/gVisor...")

# Get sandbox service endpoint via port-forward
print("\nTo test direct sandbox execution, run in another terminal:")
print("kubectl port-forward svc/execution-sandbox-svc 8004:8004 -n qlp-production")
print("\nThen run: python test_direct_kata_sandbox.py")