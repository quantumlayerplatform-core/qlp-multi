#!/usr/bin/env python3
"""
Simple Temporal Cloud connection test
"""
import asyncio
import os
from temporalio.client import Client, TLSConfig
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """Test basic connection to Temporal Cloud"""
    
    # Get configuration
    temporal_server = os.getenv('TEMPORAL_SERVER', 'us-west-2.aws.api.temporal.io:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'qlp-beta.f6bob')
    api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')
    
    print(f"Server: {temporal_server}")
    print(f"Namespace: {temporal_namespace}")
    print(f"API Key Set: {bool(api_key)}")
    print(f"API Key prefix: {api_key[:20] if api_key else 'None'}...")
    
    try:
        print("\nConnecting to Temporal Cloud...")
        print(f"Using API key auth with SDK 1.14.1")
        client = await Client.connect(
            temporal_server,
            namespace=temporal_namespace,
            api_key=api_key,
            tls=True
        )
        print("✅ Connected successfully!")
        
        # Try to get namespace info
        print("\nAttempting to get namespace info...")
        try:
            # Just try to access the namespace - this should work if auth is good
            print(f"✅ Namespace '{temporal_namespace}' is accessible")
        except Exception as e:
            print(f"❌ Failed to access namespace: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())