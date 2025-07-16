#!/usr/bin/env python3
"""
Test rate limiting with multiple concurrent requests
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Base URL
BASE_URL = "http://localhost:8000"

# Test tasks with varying complexity
TEST_TASKS = [
    {
        "tenant_id": "test-tenant-1",
        "user_id": "test-user-1",
        "description": "Create a Python function to calculate fibonacci sequence"
    },
    {
        "tenant_id": "test-tenant-2",
        "user_id": "test-user-2",
        "description": "Build a JavaScript React component for a todo list"
    },
    {
        "tenant_id": "test-tenant-3",
        "user_id": "test-user-3",
        "description": "Write a Go HTTP server with middleware"
    },
    {
        "tenant_id": "test-tenant-4",
        "user_id": "test-user-4",
        "description": "Create a SQL query to find top 10 customers by revenue"
    },
    {
        "tenant_id": "test-tenant-5",
        "user_id": "test-user-5",
        "description": "Implement a binary search tree in Java"
    }
]

async def execute_task(session, task_data, task_id):
    """Execute a single task and track timing"""
    start_time = time.time()
    
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_id}: Submitting - {task_data['description'][:50]}...")
        
        async with session.post(f"{BASE_URL}/execute", json=task_data) as response:
            if response.status == 200:
                result = await response.json()
                workflow_id = result.get("workflow_id")
                elapsed = time.time() - start_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_id}: SUCCESS - Workflow {workflow_id} (took {elapsed:.2f}s)")
                return {"task_id": task_id, "status": "success", "workflow_id": workflow_id, "time": elapsed}
            else:
                error_text = await response.text()
                elapsed = time.time() - start_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_id}: FAILED - Status {response.status}: {error_text[:100]} (took {elapsed:.2f}s)")
                return {"task_id": task_id, "status": "failed", "error": error_text, "time": elapsed}
                
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_id}: ERROR - {str(e)} (took {elapsed:.2f}s)")
        return {"task_id": task_id, "status": "error", "error": str(e), "time": elapsed}

async def check_workflow_status(session, workflow_id):
    """Check the status of a workflow"""
    try:
        async with session.get(f"{BASE_URL}/workflow/status/{workflow_id}") as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"status": "error", "code": response.status}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def main():
    """Run concurrent tests"""
    print(f"\n{'='*60}")
    print("Rate Limiting Test - Concurrent Requests")
    print(f"{'='*60}")
    print(f"Starting {len(TEST_TASKS)} concurrent requests at {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Create session with connection pooling
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Submit all tasks concurrently
        tasks = []
        for i, task_data in enumerate(TEST_TASKS):
            task = execute_task(session, task_data, i + 1)
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Summary statistics
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] != "success"]
        
        print(f"Total requests: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_time = sum(r["time"] for r in successful) / len(successful)
            print(f"Average response time (successful): {avg_time:.2f}s")
        
        # Check for rate limiting errors
        rate_limit_errors = [r for r in failed if "rate" in str(r.get("error", "")).lower() and "limit" in str(r.get("error", "")).lower()]
        if rate_limit_errors:
            print(f"\nRate limit errors detected: {len(rate_limit_errors)}")
            for r in rate_limit_errors:
                print(f"  - Task {r['task_id']}: {r['error'][:100]}")
        
        # Wait a bit then check workflow statuses
        if successful:
            print(f"\n{'='*60}")
            print("WORKFLOW STATUS CHECK (after 20 seconds)")
            print(f"{'='*60}")
            await asyncio.sleep(20)
            
            for result in successful[:3]:  # Check first 3 workflows
                workflow_id = result["workflow_id"]
                status = await check_workflow_status(session, workflow_id)
                print(f"Workflow {workflow_id}: {status.get('status', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(main())