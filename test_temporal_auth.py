import asyncio
from temporalio.client import Client
import os
from dotenv import load_dotenv

# Load cloud environment
load_dotenv('.env.cloud')

async def main():
    # Get the API key from environment
    TEMPORAL_AUTH_TOKEN = os.getenv("TEMPORAL_CLOUD_API_KEY")
    
    client = await Client.connect(
        "us-west-2.aws.api.temporal.io:7233",
        namespace="qlp-beta.f6bob",
        tls=True,  # Enable TLS for Temporal Cloud
        rpc_metadata={"authorization": f"Bearer {TEMPORAL_AUTH_TOKEN}"}
    )
    
    try:
        # Try to describe namespace
        ns = await client.describe_namespace()
        print("✅ Namespace info:", ns)
    except Exception as e:
        print(f"❌ Failed to describe namespace: {e}")
        
        # Try to list workflows instead
        print("\nTrying to list workflows...")
        workflows = []
        async for wf in client.list_workflows(query="", page_size=5):
            workflows.append(wf)
        print(f"✅ Found {len(workflows)} workflows")

if __name__ == "__main__":
    asyncio.run(main())