#!/usr/bin/env python3
"""
Minimal Temporal Cloud connection test
"""
import asyncio
import os
from temporalio.client import Client, TLSConfig
from dotenv import load_dotenv

load_dotenv('.env.cloud')

async def test_connection():
    server = os.getenv('TEMPORAL_CLOUD_ENDPOINT', 'us-west-2.aws.api.temporal.io:7233')
    namespace = os.getenv('TEMPORAL_CLOUD_NAMESPACE', 'qlp-beta.f6bob')
    api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
    
    print(f"Server: {server}")
    print(f"Namespace: {namespace}")
    print(f"API Key: {'Present' if api_key else 'Missing'}")
    
    # Try different connection methods
    methods = [
        {
            "name": "Method 1: api_key parameter",
            "connect": lambda: Client.connect(
                target_host=server,
                namespace=namespace,
                api_key=api_key,
                tls=True
            )
        },
        {
            "name": "Method 2: RPC metadata",
            "connect": lambda: Client.connect(
                target_host=server,
                namespace=namespace,
                tls=True,
                rpc_metadata={"authorization": f"Bearer {api_key}"}
            )
        },
        {
            "name": "Method 3: TLSConfig with metadata",
            "connect": lambda: Client.connect(
                target_host=server,
                namespace=namespace,
                tls=TLSConfig(),
                rpc_metadata={"authorization": f"Bearer {api_key}"}
            )
        }
    ]
    
    for method in methods:
        print(f"\n🔍 Trying {method['name']}...")
        try:
            client = await method['connect']()
            print("✅ SUCCESS! Connected to Temporal Cloud")
            
            # Try to list workflows to verify connection
            workflows = []
            async for wf in client.list_workflows(query="", page_size=1):
                workflows.append(wf)
                break
            print(f"   Verified: Can list workflows")
            return True
            
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}: {str(e)[:200]}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_connection())