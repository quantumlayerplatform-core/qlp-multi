#!/usr/bin/env python3
"""
Terminate stuck workflows in Temporal
"""

import asyncio
import sys
from temporalio.client import Client

async def terminate_workflow(client, workflow_id, reason="Stuck workflow - manual termination"):
    """Terminate a single workflow"""
    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.terminate(reason)
        print(f"✅ Terminated: {workflow_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to terminate {workflow_id}: {e}")
        return False

async def main():
    """Terminate stuck workflows"""
    
    if len(sys.argv) > 1:
        # Specific workflow IDs provided
        workflow_ids = sys.argv[1:]
    else:
        # Try to read from saved file
        try:
            with open("/tmp/stuck_workflows.txt", "r") as f:
                workflow_ids = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("❌ No workflow IDs provided and no stuck workflows file found")
            print("\nUsage:")
            print("  python3 scripts/terminate_workflows.py <workflow_id1> <workflow_id2> ...")
            print("  OR")
            print("  python3 scripts/check_stuck_workflows.py  # to identify stuck workflows first")
            return
    
    if not workflow_ids:
        print("❌ No workflows to terminate")
        return
        
    # Connect to Temporal
    client = await Client.connect("localhost:7233")
    
    print(f"🔧 Terminating {len(workflow_ids)} workflows...")
    print("=" * 60)
    
    # Terminate each workflow
    success_count = 0
    for wf_id in workflow_ids:
        if await terminate_workflow(client, wf_id):
            success_count += 1
    
    print("=" * 60)
    print(f"\n📊 Summary: {success_count}/{len(workflow_ids)} workflows terminated")
    
    # Also terminate the specific GitHub workflow mentioned
    github_workflow = "qlp-github-821f5aa8-4bf1-43a8-9c97-1bdfa0e0db95"
    if github_workflow not in workflow_ids:
        print(f"\n🔧 Also terminating known stuck workflow: {github_workflow}")
        await terminate_workflow(client, github_workflow)

if __name__ == "__main__":
    asyncio.run(main())