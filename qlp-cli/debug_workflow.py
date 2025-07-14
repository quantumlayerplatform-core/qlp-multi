#!/usr/bin/env python3
"""
Debug workflow status responses
"""

import httpx
import asyncio
import json
import sys

async def check_workflow(workflow_id):
    """Check workflow status and print response"""
    
    print(f"Checking workflow: {workflow_id}")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        # Try both endpoints
        endpoints = [
            f"http://localhost:8000/status/{workflow_id}",
            f"http://localhost:8000/workflow/status/{workflow_id}"
        ]
        
        for endpoint in endpoints:
            print(f"\nTrying: {endpoint}")
            try:
                response = await client.get(endpoint)
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(json.dumps(data, indent=2))
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_workflow.py <workflow_id>")
        sys.exit(1)
    
    workflow_id = sys.argv[1]
    asyncio.run(check_workflow(workflow_id))