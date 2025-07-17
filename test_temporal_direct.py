#!/usr/bin/env python3
"""
Direct Temporal Cloud connection test using the correct approach
"""
import asyncio
import os
from temporalio.client import Client
from dotenv import load_dotenv

load_dotenv('.env.cloud')

async def main():
    api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
    
    client = await Client.connect(
        "us-west-2.aws.api.temporal.io:7233",
        namespace="qlp-beta.f6bob",
        rpc_metadata={
            "authorization": f"Bearer {api_key}"
        }
    )
    print("✅ Connected to Temporal Cloud successfully!")
    
    # List workflows to verify
    workflows = []
    async for wf in client.list_workflows(query="", page_size=5):
        workflows.append(wf)
    
    print(f"Found {len(workflows)} workflows in namespace")
    for wf in workflows:
        print(f"  - {wf.id}: {wf.status}")

if __name__ == "__main__":
    asyncio.run(main())