#!/usr/bin/env python3
"""
Test different Temporal authentication methods
"""
import asyncio
import os
from temporalio.client import Client, TLSConfig
from temporalio.service import RPCError
from dotenv import load_dotenv

load_dotenv()

async def test_methods():
    """Test different auth methods"""
    
    temporal_server = os.getenv('TEMPORAL_SERVER', 'us-west-2.aws.api.temporal.io:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'qlp-beta.f6bob')
    api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
    
    print(f"Server: {temporal_server}")
    print(f"Namespace: {temporal_namespace}")
    
    # Method 1: Using headers with custom key
    print("\n1. Testing with api-key header...")
    try:
        client = await Client.connect(
            temporal_server,
            namespace=temporal_namespace,
            rpc_metadata={"api-key": api_key},
            tls=True
        )
        print("✅ Connected with api-key header!")
        # Test by listing workflows
        workflows = []
        async for wf in client.list_workflows():
            workflows.append(wf)
            break
        print("✅ Successfully accessed namespace!")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Method 2: Using temporal-api-key header
    print("\n2. Testing with temporal-api-key header...")
    try:
        client = await Client.connect(
            temporal_server,
            namespace=temporal_namespace,
            rpc_metadata={"temporal-api-key": api_key},
            tls=True
        )
        print("✅ Connected with temporal-api-key header!")
        workflows = []
        async for wf in client.list_workflows():
            workflows.append(wf)
            break
        print("✅ Successfully accessed namespace!")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Method 3: Using authorization Bearer header
    print("\n3. Testing with Authorization Bearer header...")
    try:
        client = await Client.connect(
            temporal_server,
            namespace=temporal_namespace,
            rpc_metadata={"authorization": f"Bearer {api_key}"},
            tls=True
        )
        print("✅ Connected with Authorization Bearer!")
        workflows = []
        async for wf in client.list_workflows():
            workflows.append(wf)
            break
        print("✅ Successfully accessed namespace!")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Method 4: Using x-temporal-api-key header
    print("\n4. Testing with x-temporal-api-key header...")
    try:
        client = await Client.connect(
            temporal_server,
            namespace=temporal_namespace,
            rpc_metadata={"x-temporal-api-key": api_key},
            tls=True
        )
        print("✅ Connected with x-temporal-api-key header!")
        workflows = []
        async for wf in client.list_workflows():
            workflows.append(wf)
            break
        print("✅ Successfully accessed namespace!")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_methods())