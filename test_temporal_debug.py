import asyncio
from temporalio.client import Client
import os
from dotenv import load_dotenv
import jwt
import json

# Load cloud environment
load_dotenv('.env.cloud')

async def main():
    # Get the API key from environment
    TEMPORAL_AUTH_TOKEN = os.getenv("TEMPORAL_CLOUD_API_KEY")
    
    # Decode the JWT to check its contents
    print("🔍 Analyzing API Key...")
    try:
        decoded = jwt.decode(TEMPORAL_AUTH_TOKEN, options={"verify_signature": False})
        print(f"Account ID: {decoded.get('account_id')}")
        print(f"Key ID: {decoded.get('key_id')}")
        print(f"Expiration: {decoded.get('exp')}")
    except Exception as e:
        print(f"Failed to decode JWT: {e}")
    
    # Try different connection approaches
    approaches = [
        {
            "name": "With tls=True",
            "kwargs": {
                "target_host": "us-west-2.aws.api.temporal.io:7233",
                "namespace": "qlp-beta.f6bob",
                "tls": True,
                "rpc_metadata": {"authorization": f"Bearer {TEMPORAL_AUTH_TOKEN}"}
            }
        },
        {
            "name": "Without explicit TLS",
            "kwargs": {
                "target_host": "us-west-2.aws.api.temporal.io:7233",
                "namespace": "qlp-beta.f6bob",
                "rpc_metadata": {"authorization": f"Bearer {TEMPORAL_AUTH_TOKEN}"}
            }
        },
        {
            "name": "With grpc:// prefix",
            "kwargs": {
                "target_host": "grpc://us-west-2.aws.api.temporal.io:7233",
                "namespace": "qlp-beta.f6bob",
                "rpc_metadata": {"authorization": f"Bearer {TEMPORAL_AUTH_TOKEN}"}
            }
        }
    ]
    
    for approach in approaches:
        print(f"\n🔍 Trying: {approach['name']}")
        try:
            client = await Client.connect(**approach['kwargs'])
            print("✅ Connected!")
            
            # Try to list workflows
            workflows = []
            async for wf in client.list_workflows(query="", page_size=1):
                workflows.append(wf)
                break
            print(f"✅ Successfully listed workflows! Count: {len(workflows)}")
            return
            
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}: {str(e)[:200]}")

if __name__ == "__main__":
    asyncio.run(main())