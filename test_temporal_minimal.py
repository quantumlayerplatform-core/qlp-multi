#!/usr/bin/env python3
"""Minimal test for Temporal connection issue"""

import asyncio
from temporalio.client import Client

async def test_direct():
    """Test direct connection"""
    try:
        print("Test 1: Direct connection")
        client = await Client.connect("temporal:7233")
        print("✅ Direct connection successful")
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")

async def test_with_settings():
    """Test with settings"""
    try:
        print("\nTest 2: Connection with settings")
        from src.common.config import settings
        client = await Client.connect(settings.TEMPORAL_SERVER)
        print("✅ Settings connection successful")
    except Exception as e:
        print(f"❌ Settings connection failed: {e}")

async def test_from_api_context():
    """Test from API context"""
    try:
        print("\nTest 3: Connection from API context")
        from src.api.v2.marketing_api import get_temporal_client
        client = await get_temporal_client()
        print("✅ API context connection successful")
    except Exception as e:
        print(f"❌ API context connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct())
    asyncio.run(test_with_settings())
    asyncio.run(test_from_api_context())