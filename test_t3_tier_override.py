#!/usr/bin/env python3
"""
Test script to demonstrate explicit T3 tier selection
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_t3_override():
    """Test execution with explicit T3 tier selection"""
    
    # Complex task that would benefit from T3 meta-agent capabilities
    request = {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "description": """
        Create a complete microservices architecture for an e-commerce platform with:
        - User service with authentication
        - Product catalog service
        - Shopping cart service
        - Order processing service
        - Payment integration
        - API Gateway
        - Service discovery
        - Load balancing
        - Monitoring and logging
        Each service should have its own database, API documentation, and tests.
        """,
        "requirements": "Production-ready code with comprehensive error handling and security",
        "tier_override": "T3"  # Force T3 tier for all tasks
    }
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        print(f"\n[{datetime.now()}] Submitting request with T3 tier override...")
        print(f"Description: {request['description'][:100]}...")
        print(f"Tier Override: {request['tier_override']}")
        
        # Submit the request
        response = await client.post(
            "http://localhost:8000/execute",
            json=request
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return
        
        result = response.json()
        workflow_id = result["workflow_id"]
        print(f"\nWorkflow started: {workflow_id}")
        
        # Poll for status
        print("\nMonitoring workflow progress...")
        while True:
            status_response = await client.get(f"http://localhost:8000/status/{workflow_id}")
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"[{datetime.now()}] Status: {status['status']}")
                
                if status['status'] in ['completed', 'failed']:
                    print(f"\nWorkflow {status['status']}!")
                    if status.get('result'):
                        print(f"Result: {json.dumps(status['result'], indent=2)}")
                    break
            
            await asyncio.sleep(5)

async def test_mixed_tiers():
    """Test with default tier selection vs T3 override"""
    
    simple_request = {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "description": "Create a simple Python function to calculate factorial",
        # No tier_override - will use automatic selection (likely T0)
    }
    
    complex_request = {
        "tenant_id": "test-tenant", 
        "user_id": "test-user",
        "description": "Create a simple Python function to calculate factorial",
        "tier_override": "T3"  # Force T3 even for simple task
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Automatic tier selection
        print("\n=== Test 1: Automatic Tier Selection ===")
        response1 = await client.post("http://localhost:8000/execute", json=simple_request)
        result1 = response1.json()
        print(f"Workflow ID: {result1['workflow_id']}")
        
        # Test 2: T3 override
        print("\n=== Test 2: T3 Tier Override ===")
        response2 = await client.post("http://localhost:8000/execute", json=complex_request)
        result2 = response2.json()
        print(f"Workflow ID: {result2['workflow_id']}")
        
        # Wait a bit and check both statuses
        await asyncio.sleep(10)
        
        for workflow_id, test_name in [(result1['workflow_id'], "Automatic"), 
                                       (result2['workflow_id'], "T3 Override")]:
            status_response = await client.get(f"http://localhost:8000/status/{workflow_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"\n{test_name} - Status: {status['status']}")

async def test_partial_t3_override():
    """Test with tier override only for specific task types"""
    
    request = {
        "tenant_id": "test-tenant",
        "user_id": "test-user", 
        "description": "Build a REST API with database integration and authentication",
        "metadata": {
            # You could implement more granular control in the future
            "tier_preferences": {
                "architecture_design": "T3",
                "code_generation": "T1",
                "test_creation": "T0"
            }
        },
        "tier_override": "T2"  # Default override for all tasks
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n=== Test: Partial T3 Override ===")
        response = await client.post("http://localhost:8000/execute", json=request)
        result = response.json()
        print(f"Workflow ID: {result['workflow_id']}")
        print(f"Default Tier Override: T2")
        print(f"Task-specific preferences: {request['metadata']['tier_preferences']}")

if __name__ == "__main__":
    print("QLP T3 Tier Override Test")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_t3_override())
    # asyncio.run(test_mixed_tiers())
    # asyncio.run(test_partial_t3_override())