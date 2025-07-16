#!/usr/bin/env python3
"""
Test the /execute endpoint with proper waiting for workflow completion
"""

import requests
import time
import json
import sys

def test_execute_endpoint():
    """Test the /execute endpoint and wait for completion"""
    
    # Step 1: Submit the execution request
    print("🚀 Testing /execute endpoint")
    print("=" * 50)
    
    execute_url = "http://localhost:8000/execute"
    payload = {
        "tenant_id": "test",
        "user_id": "developer",
        "description": "Create a Python class called StringAnalyzer that analyzes text. It should have methods to count words, count characters, find the most common word, and calculate average word length. Include proper error handling and comprehensive unit tests."
    }
    
    print("\n📤 Submitting execution request...")
    print(f"Description: {payload['description'][:100]}...")
    
    response = requests.post(execute_url, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to submit request: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    workflow_id = result.get("workflow_id")
    
    print(f"✅ Workflow submitted: {workflow_id}")
    
    # Step 2: Poll for workflow completion
    print("\n⏳ Waiting for workflow to complete...")
    
    status_url = f"http://localhost:8000/workflow/status/{workflow_id}"
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(5)  # Wait 5 seconds between checks
        attempt += 1
        
        status_response = requests.get(status_url)
        if status_response.status_code != 200:
            print(f"❌ Failed to get status: {status_response.status_code}")
            continue
        
        status_data = status_response.json()
        workflow_status = status_data.get("workflow_status", "UNKNOWN")
        
        print(f"   Status: {workflow_status} (attempt {attempt}/{max_attempts})")
        
        if workflow_status == "COMPLETED":
            print("✅ Workflow completed!")
            
            # Try to get the capsule ID from the result
            if "result" in status_data and isinstance(status_data["result"], dict):
                capsule_id = status_data["result"].get("capsule_id")
                if capsule_id:
                    print(f"\n📦 Capsule created: {capsule_id}")
                    
                    # Get capsule details
                    capsule_url = f"http://localhost:8000/api/capsules/{capsule_id}"
                    capsule_response = requests.get(capsule_url)
                    
                    if capsule_response.status_code == 200:
                        capsule_data = capsule_response.json()
                        
                        print("\n📋 Capsule Details:")
                        print(f"   Name: {capsule_data.get('manifest', {}).get('name', 'N/A')}")
                        print(f"   Language: {capsule_data.get('manifest', {}).get('language', 'N/A')}")
                        
                        # Show files
                        source_files = list(capsule_data.get('source_code', {}).keys())
                        test_files = list(capsule_data.get('tests', {}).keys())
                        
                        print(f"\n📂 Files generated:")
                        print(f"   Source files: {', '.join(source_files)}")
                        print(f"   Test files: {', '.join(test_files)}")
                        
                        # Show sample code
                        if source_files:
                            first_file = source_files[0]
                            code = capsule_data['source_code'][first_file]
                            print(f"\n📄 Sample code from {first_file}:")
                            print("-" * 50)
                            print(code[:500] + "..." if len(code) > 500 else code)
                            print("-" * 50)
                        
                        # Test download
                        print("\n💾 Testing download endpoint...")
                        download_url = f"http://localhost:8000/api/capsules/{capsule_id}/download"
                        download_response = requests.get(download_url, params={"format": "zip"})
                        
                        if download_response.status_code == 200:
                            print(f"✅ Download successful! (Size: {len(download_response.content)} bytes)")
                        else:
                            print(f"❌ Download failed: {download_response.status_code}")
                    
                    else:
                        print(f"❌ Failed to get capsule details: {capsule_response.status_code}")
                
                else:
                    print("⚠️  No capsule ID in result")
                    print(f"Result: {json.dumps(status_data.get('result', {}), indent=2)}")
            
            break
            
        elif workflow_status in ["FAILED", "TERMINATED", "CANCELED"]:
            print(f"❌ Workflow {workflow_status}")
            if "result" in status_data:
                print(f"Error: {json.dumps(status_data['result'], indent=2)}")
            break
    
    else:
        print("⏱️  Timeout waiting for workflow completion")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    try:
        test_execute_endpoint()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)