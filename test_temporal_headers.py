#\!/usr/bin/env python3
"""
Test different header formats for Temporal Cloud
"""
import asyncio
import os
from temporalio.client import Client, TLSConfig
from dotenv import load_dotenv

load_dotenv('.env.cloud')

async def test_headers():
    server = os.getenv('TEMPORAL_CLOUD_ENDPOINT', 'us-west-2.aws.api.temporal.io:7233')
    namespace = os.getenv('TEMPORAL_CLOUD_NAMESPACE', 'qlp-beta.f6bob')
    api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
    
    print(f"Testing different header formats...")
    
    # Different header formats to try
    header_formats = [
        {
            "name": "Bearer token",
            "headers": {"authorization": f"Bearer {api_key}"}
        },
        {
            "name": "API key header",
            "headers": {"temporal-api-key": api_key}
        },
        {
            "name": "X-API-Key",
            "headers": {"x-api-key": api_key}
        },
        {
            "name": "Bearer with namespace",
            "headers": {
                "authorization": f"Bearer {api_key}",
                "temporal-namespace": namespace
            }
        }
    ]
    
    for fmt in header_formats:
        print(f"\n🔍 Trying {fmt['name']}...")
        try:
            client = await Client.connect(
                target_host=server,
                namespace=namespace,
                tls=True,
                rpc_metadata=fmt['headers']
            )
            print("✅ SUCCESS\!")
            return True
        except Exception as e:
            print(f"❌ Failed: {str(e)[:150]}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_headers())
