#!/usr/bin/env python3
"""
Test the /execute endpoint functionality
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_execute_endpoint():
    print("🚀 Testing /execute Endpoint")
    print("=" * 50)
    
    # Simple request
    request_data = {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "description": "Create a simple Python function that adds two numbers and returns the result",
        "requirements": "Include type hints and a docstring",
        "metadata": {
            "project_name": "Simple Calculator",
            "complexity": "trivial"
        }
    }
    
    print("\n📝 Submitting execution request...")
    print(f"Description: {request_data['description']}")
    
    # Submit request
    response = requests.post(f"{BASE_URL}/execute", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        workflow_id = result["workflow_id"]
        print(f"\n✅ Workflow submitted successfully!")
        print(f"Workflow ID: {workflow_id}")
        print(f"Status: {result['status']}")
        
        # Poll for completion
        print("\n⏳ Waiting for completion...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            
            # Check status
            status_response = requests.get(f"{BASE_URL}/status/{workflow_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                current_status = status["status"]
                
                if current_status == "COMPLETED":
                    print(f"\n✅ Workflow completed in ~{i+1} seconds!")
                    print(f"Start time: {status['start_time']}")
                    print(f"End time: {status['close_time']}")
                    
                    # Try to get the capsule
                    execution_id = workflow_id.replace("qlp-execution-", "")
                    capsule_response = requests.get(f"{BASE_URL}/capsule/{execution_id}")
                    
                    if capsule_response.status_code == 200:
                        print("\n📦 Capsule generated successfully!")
                        # Show a preview of the generated code
                        capsule_data = capsule_response.json()
                        if "source_code" in capsule_data:
                            for file_name, content in list(capsule_data["source_code"].items())[:1]:
                                print(f"\n📄 Generated file: {file_name}")
                                print("-" * 40)
                                print(content[:500] + "..." if len(content) > 500 else content)
                    break
                    
                elif current_status == "FAILED":
                    print(f"\n❌ Workflow failed!")
                    break
                else:
                    print(f"\r⏳ Status: {current_status} ({i+1}s)...", end="", flush=True)
            
        else:
            print(f"\n⚠️ Workflow still running after 30 seconds")
            
    else:
        print(f"\n❌ Request failed: {response.status_code}")
        print(response.text)

def check_running_workflows():
    """Check if there are any running workflows"""
    print("\n📊 Checking Running Workflows")
    print("=" * 50)
    
    # The actual endpoint to list workflows would depend on your implementation
    # For now, let's check our test workflow
    test_ids = [
        "qlp-execution-ca3b416f-68e2-4ca3-a8f3-3649efd9fa38",
        "qlp-execution-2ae651c2-3bb0-41ae-bdee-68a8977ccdf3"
    ]
    
    for workflow_id in test_ids:
        response = requests.get(f"{BASE_URL}/status/{workflow_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"\nWorkflow: {workflow_id}")
            print(f"Status: {status['status']}")
            print(f"Started: {status.get('start_time', 'N/A')}")
            print(f"Completed: {status.get('close_time', 'N/A')}")

if __name__ == "__main__":
    print("Testing Quantum Layer Platform /execute Endpoint\n")
    
    # Test the execute endpoint
    test_execute_endpoint()
    
    # Check running workflows
    check_running_workflows()
    
    print("\n✅ Test complete!")