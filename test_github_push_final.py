#!/usr/bin/env python3
"""
Final test for GitHub push integration
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
    print("ERROR: GITHUB_TOKEN not found in environment")
    exit(1)

print(f"✅ GitHub token found: {GITHUB_TOKEN[:10]}...")

# Test endpoint
url = "http://localhost:8000/generate/complete-with-github"

# Test data
data = {
    "description": "Create a Python calculator with add, subtract, multiply, and divide functions, including unit tests",
    "github_token": GITHUB_TOKEN,
    "repo_name": f"qlp-calculator-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    "private": False
}

print(f"\n🚀 Starting GitHub push test...")
print(f"Repository name: {data['repo_name']}")

# Make request
response = requests.post(url, json=data)
print(f"\nResponse status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"✅ Workflow started successfully!")
    print(f"Workflow ID: {result['workflow_id']}")
    print(f"Request ID: {result['request_id']}")
    
    # Monitor workflow
    status_url = f"http://localhost:8000{result['status_check_url']}"
    print(f"\n📊 Monitoring workflow progress...")
    
    for i in range(30):  # Check for up to 5 minutes
        time.sleep(10)
        status_response = requests.get(status_url)
        
        if status_response.status_code == 200:
            status = status_response.json()
            workflow_status = status.get('workflow_status', 'UNKNOWN')
            print(f"[{i+1}/30] Status: {workflow_status}")
            
            if workflow_status == 'COMPLETED':
                print("\n✅ Workflow completed successfully!")
                
                # Get the final result
                final_url = f"http://localhost:8000/workflow/result/{result['workflow_id']}"
                final_response = requests.get(final_url)
                
                if final_response.status_code == 200:
                    final_result = final_response.json()
                    
                    if 'github_url' in final_result:
                        print(f"\n🎉 GitHub Repository Created!")
                        print(f"URL: {final_result['github_url']}")
                    else:
                        print("\n❌ GitHub URL not found in result")
                        print(json.dumps(final_result, indent=2))
                break
            elif workflow_status == 'FAILED':
                print("\n❌ Workflow failed!")
                # Try to get error details
                error_url = f"http://localhost:8000/workflow/result/{result['workflow_id']}"
                error_response = requests.get(error_url)
                if error_response.status_code == 200:
                    print("Error details:")
                    print(json.dumps(error_response.json(), indent=2))
                break
    else:
        print("\n⏱️ Workflow still running after 5 minutes")
else:
    print(f"❌ Failed to start workflow: {response.status_code}")
    print(response.text)