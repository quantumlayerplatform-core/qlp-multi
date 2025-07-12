#!/usr/bin/env python3
"""
Check and manage stuck workflows in Temporal
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from temporalio.client import Client
import json

async def main():
    """Check for stuck workflows"""
    
    # Connect to Temporal
    client = await Client.connect("localhost:7233")
    
    print("🔍 Checking for running workflows...")
    print("=" * 80)
    
    # List all running workflows
    running_workflows = []
    async for workflow in client.list_workflows(
        query='ExecutionStatus="Running"'
    ):
        running_workflows.append(workflow)
        
    if not running_workflows:
        print("✅ No running workflows found")
        return
        
    print(f"\n📊 Found {len(running_workflows)} running workflows:\n")
    
    # Analyze each workflow
    stuck_candidates = []
    for wf in running_workflows:
        # Calculate runtime
        start_time = wf.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        
        runtime = datetime.now(timezone.utc) - start_time
        hours = runtime.total_seconds() / 3600
        
        # Workflow details
        print(f"Workflow ID: {wf.id}")
        print(f"Type: {wf.workflow_type}")
        print(f"Task Queue: {wf.task_queue}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Runtime: {hours:.1f} hours")
        
        # Check if it's likely stuck (running for more than 1 hour)
        if hours > 1:
            print("⚠️  LIKELY STUCK (running > 1 hour)")
            stuck_candidates.append(wf)
            
        # Try to get current state
        try:
            handle = client.get_workflow_handle(wf.id)
            # Try to query workflow state if it has queries
            print(f"Status: Running")
        except Exception as e:
            print(f"Status: Unable to query - {str(e)}")
            
        print("-" * 40)
    
    # Provide cleanup options
    if stuck_candidates:
        print(f"\n⚠️  Found {len(stuck_candidates)} potentially stuck workflows")
        print("\nTo terminate stuck workflows, run:")
        print("python3 scripts/terminate_workflows.py")
        
        # Save workflow IDs for easy termination
        with open("/tmp/stuck_workflows.txt", "w") as f:
            for wf in stuck_candidates:
                f.write(f"{wf.id}\n")
        print("\nStuck workflow IDs saved to: /tmp/stuck_workflows.txt")
    else:
        print("\n✅ All workflows appear to be running normally")

if __name__ == "__main__":
    asyncio.run(main())