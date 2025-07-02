#!/usr/bin/env python3
"""
Test script to verify Azure OpenAI integration is working properly
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_azure_integration():
    """Test the full workflow with Azure OpenAI"""
    
    print("=== Testing QLP with Azure OpenAI ===")
    print(f"Time: {datetime.now()}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Submit a request
        print("\n1. Submitting request to orchestrator...")
        request_data = {
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "description": "Create a simple Python function that calculates the factorial of a number with proper error handling",
            "requirements": "Include input validation and handle negative numbers",
            "constraints": {
                "language": "python",
                "max_lines": 20
            }
        }
        
        try:
            response = await client.post(
                "http://localhost:8000/execute",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()
            request_id = result.get("workflow_id", result.get("request_id"))
            print(f"✓ Request submitted: {request_id}")
        except Exception as e:
            print(f"✗ Failed to submit request: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return
        
        # 2. Poll for status
        print("\n2. Checking request status...")
        max_polls = 10
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                status_response = await client.get(
                    f"http://localhost:8000/status/{request_id}"
                )
                status_response.raise_for_status()
                status = status_response.json()
                
                print(f"   Status: {status['status']} (poll {poll_count + 1}/{max_polls})")
                
                if status['status'] in ['completed', 'failed']:
                    print(f"\n✓ Request {status['status']}")
                    print(f"Results: {json.dumps(status, indent=2)}")
                    break
                    
            except Exception as e:
                print(f"   Error checking status: {e}")
            
            poll_count += 1
            await asyncio.sleep(3)
        
        # 3. Test agent directly
        print("\n3. Testing agent service directly...")
        agent_request = {
            "task": {
                "id": "test-task-123",
                "type": "code_generation",
                "description": "Write a hello world function in Python",
                "complexity": "trivial",
                "status": "pending",
                "metadata": {}
            },
            "tier": "T0",
            "context": {}
        }
        
        try:
            agent_response = await client.post(
                "http://localhost:8001/execute",
                json=agent_request
            )
            agent_response.raise_for_status()
            agent_result = agent_response.json()
            print(f"✓ Agent executed successfully")
            print(f"Agent result: {json.dumps(agent_result, indent=2)}")
        except Exception as e:
            print(f"✗ Agent execution failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    asyncio.run(test_azure_integration())