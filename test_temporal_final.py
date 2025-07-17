#!/usr/bin/env python3
"""
Final Temporal Cloud connection test
"""
import asyncio
import os
from temporalio.client import Client, TLSConfig
from dotenv import load_dotenv

# Load cloud environment
load_dotenv('.env.cloud')

async def test_temporal_cloud():
    """Test Temporal Cloud connection"""
    print("🔍 Testing Temporal Cloud connection...")
    
    # Configuration
    endpoint = "us-west-2.aws.api.temporal.io:7233"
    namespace = "qlp-beta.f6bob"
    api_key = os.getenv("TEMPORAL_CLOUD_API_KEY")
    
    if not api_key:
        print("❌ TEMPORAL_CLOUD_API_KEY not found in environment")
        return False
    
    print(f"Endpoint: {endpoint}")
    print(f"Namespace: {namespace}")
    print(f"API Key: Present ({len(api_key)} chars)")
    
    try:
        # Connect with TLS enabled and API key in headers
        client = await Client.connect(
            endpoint,
            namespace=namespace,
            tls=True,
            rpc_metadata={
                "authorization": f"Bearer {api_key}"
            }
        )
        
        print("✅ Connected to Temporal Cloud!")
        
        # Try to list workflows
        print("\nListing workflows...")
        workflow_count = 0
        async for workflow in client.list_workflows(page_size=10):
            workflow_count += 1
            print(f"  - {workflow.id} ({workflow.status.name})")
            if workflow_count >= 5:  # Limit to first 5
                break
        
        if workflow_count == 0:
            print("  No workflows found (namespace is empty)")
        else:
            print(f"  Total shown: {workflow_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        
        # Additional debugging
        if "unauthorized" in str(e).lower():
            print("\n💡 Authorization failed. Possible issues:")
            print("  1. API key might be invalid or expired")
            print("  2. API key might not have permissions for this namespace")
            print("  3. Namespace name might be incorrect")
            print("\nPlease verify:")
            print("  - The API key was created for namespace 'qlp-beta.f6bob'")
            print("  - The API key has not expired")
            print("  - You have the correct permissions")
            
        return False

async def main():
    # Test Temporal Cloud
    success = await test_temporal_cloud()
    
    if success:
        print("\n🎉 Temporal Cloud is working!")
        print("\nNext steps:")
        print("1. Your services can now use Temporal Cloud")
        print("2. Update docker-compose.cloud-services.yml to remove local Temporal")
        print("3. All workflows will be managed in the cloud")
    else:
        print("\n⚠️  Temporal Cloud connection failed")
        print("For now, you can continue using local Temporal")

if __name__ == "__main__":
    asyncio.run(main())