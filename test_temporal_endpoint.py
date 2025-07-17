#\!/usr/bin/env python3
"""
Test different endpoint formats
"""
import asyncio
import os
from temporalio.client import Client, TLSConfig
from dotenv import load_dotenv

load_dotenv('.env.cloud')

async def test_endpoints():
    namespace = os.getenv('TEMPORAL_CLOUD_NAMESPACE', 'qlp-beta.f6bob')
    api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
    
    # Different endpoint formats
    endpoints = [
        "qlp-beta.f6bob.tmprl.cloud:7233",
        "us-west-2.aws.api.temporal.io:7233",
        "qlp-beta-f6bob.us-west-2.aws.api.temporal.io:7233",
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Trying endpoint: {endpoint}")
        try:
            client = await Client.connect(
                target_host=endpoint,
                namespace=namespace,
                tls=True,
                rpc_metadata={"authorization": f"Bearer {api_key}"}
            )
            print("✅ SUCCESS\! This is the correct endpoint")
            return endpoint
        except Exception as e:
            print(f"❌ Failed: {str(e)[:100]}")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(test_endpoints())
    if result:
        print(f"\n✅ Working endpoint: {result}")
        print(f"Update TEMPORAL_CLOUD_ENDPOINT in .env.cloud to: {result}")
