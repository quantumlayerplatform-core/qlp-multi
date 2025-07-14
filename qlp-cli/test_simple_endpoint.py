#!/usr/bin/env python3
"""
Test with a simple, fast endpoint to verify CLI works
"""

import httpx
import asyncio
import json

async def test_simple():
    """Test with a simple endpoint that completes quickly"""
    
    print("Testing with simple endpoint...")
    
    # Try the health endpoint first
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
    
    # Try generating a simple capsule
    print("\nTesting capsule generation...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/generate/capsule",
            json={
                "description": "Simple hello world",
                "tenant_id": "cli-test",
                "user_id": "cli"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Capsule ID: {data.get('capsule_id')}")
            print(f"Files generated: {data.get('files_generated')}")

if __name__ == "__main__":
    asyncio.run(test_simple())