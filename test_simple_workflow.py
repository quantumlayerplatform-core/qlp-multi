#!/usr/bin/env python3
"""
Test simple workflow to verify basic functionality
"""
import requests
import json
import time

def test_simple_workflow():
    """Test with a simple request"""
    
    # Simple request
    request_data = {
        "description": "Create a Python function to calculate fibonacci numbers",
        "requirements": "Include memoization for optimization",
        "constraints": {
            "language": "Python",
            "style": "Clean and documented code"
        },
        "tenant_id": "test-tenant",
        "user_id": "test-user"
    }
    
    print("🧪 Testing Simple Workflow")
    print("=" * 50)
    
    # Start workflow
    response = requests.post(
        "http://localhost:8000/execute",
        json=request_data,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start workflow: {response.status_code}")
        print(response.text)
        return
    
    workflow_data = response.json()
    workflow_id = workflow_data.get("workflow_id")
    
    print(f"✅ Workflow started: {workflow_id}")
    
    # Monitor workflow
    start_time = time.time()
    max_duration = 300  # 5 minutes for simple workflow
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_duration:
            print(f"\n⏱️  Timeout after {elapsed:.1f} seconds")
            break
        
        try:
            status_response = requests.get(
                f"http://localhost:8000/workflow/status/{workflow_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status", "unknown")
                
                print(f"\r⏳ Status: {status} ({elapsed:.0f}s)", end="", flush=True)
                
                if status in ["completed", "failed"]:
                    print(f"\n{'✅' if status == 'completed' else '❌'} Workflow {status}")
                    print(f"⏱️  Duration: {elapsed:.1f} seconds")
                    
                    if status == "completed":
                        print(f"📦 Capsule ID: {status_data.get('capsule_id')}")
                        print(f"✨ Tasks: {status_data.get('tasks_completed')}/{status_data.get('tasks_total')}")
                    
                    return status_data
            
        except Exception as e:
            print(f"\n⚠️  Error: {str(e)}")
        
        time.sleep(2)
    
    return None

if __name__ == "__main__":
    result = test_simple_workflow()
    if result:
        print("\n✅ Simple test completed successfully!")
    else:
        print("\n❌ Simple test failed")