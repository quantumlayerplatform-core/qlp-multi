#!/usr/bin/env python3
"""
Production GitHub Push Test - The Right Way
"""
import os
import requests
import json
import time
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("❌ ERROR: GITHUB_TOKEN not found in environment")
    exit(1)

print(f"✅ GitHub token found: {GITHUB_TOKEN[:10]}...")

# Test endpoint with GitHub push metadata
url = "http://localhost:8000/execute"

# Test data with proper metadata structure
data = {
    "description": "Create a Python password generator with secure random passwords, including uppercase, lowercase, numbers, and symbols",
    "tenant_id": "prod-test",
    "user_id": "github-test-user",
    "metadata": {
        "push_to_github": True,
        "github_token": GITHUB_TOKEN,
        "github_repo_name": f"qlp-password-gen-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "github_private": False,
        "github_enterprise": True
    }
}

print(f"\n🚀 Starting Production GitHub Push Test...")
print(f"Repository name: {data['metadata']['github_repo_name']}")
print(f"Enterprise mode: {data['metadata']['github_enterprise']}")

# Make request
response = requests.post(url, json=data)
print(f"\nResponse status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"✅ Workflow started successfully!")
    print(f"Workflow ID: {result['workflow_id']}")
    print(f"Request ID: {result['request_id']}")
    
    # Monitor workflow
    workflow_id = result['workflow_id']
    print(f"\n📊 Monitoring workflow progress...")
    
    for i in range(60):  # Check for up to 10 minutes
        time.sleep(10)
        
        # Check workflow status
        status_url = f"http://localhost:8000/workflow/status/{workflow_id}"
        status_response = requests.get(status_url)
        
        if status_response.status_code == 200:
            status = status_response.json()
            workflow_status = status.get('workflow_status', 'UNKNOWN')
            print(f"[{i+1}/60] Status: {workflow_status}")
            
            if workflow_status == 'COMPLETED':
                print("\n✅ Workflow completed successfully!")
                
                # Get the final result
                result_url = f"http://localhost:8000/workflow/result/{workflow_id}"
                result_response = requests.get(result_url)
                
                if result_response.status_code == 200:
                    final_result = result_response.json()
                    
                    print("\n📋 Final Result:")
                    print(f"Capsule ID: {final_result.get('capsule_id', 'N/A')}")
                    print(f"Status: {final_result.get('status', 'N/A')}")
                    print(f"Tasks completed: {final_result.get('tasks_completed', 0)}")
                    
                    # Check for GitHub URL
                    metadata = final_result.get('metadata', {})
                    if 'github_url' in metadata:
                        print(f"\n🎉 GitHub Repository Created!")
                        print(f"URL: {metadata['github_url']}")
                        print(f"✅ PRODUCTION GITHUB PUSH SUCCESSFUL!")
                    else:
                        print(f"\n❌ GitHub URL not found in metadata")
                        print(f"Available metadata keys: {list(metadata.keys())}")
                        
                        # Check if GitHub push was attempted
                        if 'github_error' in metadata:
                            print(f"GitHub Error: {metadata['github_error']}")
                else:
                    print(f"❌ Failed to get workflow result: {result_response.status_code}")
                break
                
            elif workflow_status == 'FAILED':
                print("\n❌ Workflow failed!")
                # Get error details
                result_url = f"http://localhost:8000/workflow/result/{workflow_id}"
                result_response = requests.get(result_url)
                if result_response.status_code == 200:
                    error_result = result_response.json()
                    print("Error details:")
                    print(json.dumps(error_result, indent=2))
                break
        else:
            print(f"[{i+1}/60] Status check failed: {status_response.status_code}")
    else:
        print("\n⏱️ Workflow still running after 10 minutes")
else:
    print(f"❌ Failed to start workflow: {response.status_code}")
    print(response.text)