#!/usr/bin/env python3
"""
Test the status endpoint directly to see response format
"""

import httpx
import asyncio
import json
import sys

async def test_status(workflow_id=None):
    """Test status endpoint"""
    
    # If no workflow_id provided, start a new one first
    if not workflow_id:
        print("Starting a new workflow first...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/execute",
                json={
                    "description": "Simple test program",
                    "tenant_id": "cli-user", 
                    "user_id": "cli"
                }
            )
            if response.status_code == 200:
                data = response.json()
                workflow_id = data.get('workflow_id')
                print(f"Started workflow: {workflow_id}")
            else:
                print(f"Failed to start workflow: {response.status_code}")
                return
    
    print(f"\nChecking status for workflow: {workflow_id}")
    print("-" * 50)
    
    # Poll status
    async with httpx.AsyncClient() as client:
        for i in range(150):  # Check for up to 5 minutes
            try:
                response = await client.get(f"http://localhost:8000/status/{workflow_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"\nAttempt {i+1}:")
                    print(json.dumps(data, indent=2))
                    
                    # Check if completed
                    if 'capsule_id' in data:
                        print("\n✅ Workflow completed!")
                        break
                else:
                    print(f"\nStatus code: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"\nError: {e}")
                
            await asyncio.sleep(2)

if __name__ == "__main__":
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(test_status(workflow_id))