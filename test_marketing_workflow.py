#!/usr/bin/env python3
"""
Test Marketing Workflow Integration

Tests the complete marketing campaign generation workflow using Temporal.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v2/marketing"


async def test_campaign_generation():
    """Test creating a marketing campaign via Temporal workflow"""
    
    # Test data
    campaign_request = {
        "objective": "launch_awareness",
        "product_description": "AI-powered software development platform that automates code generation",
        "key_features": [
            "Generates production-ready code in minutes",
            "Supports multiple programming languages",
            "Includes automated testing and documentation",
            "Enterprise-grade security"
        ],
        "target_audience": "CTOs and Engineering Leaders at tech companies",
        "unique_value_prop": "Replace entire development teams with AI agents",
        "duration_days": 30,
        "channels": ["twitter", "linkedin", "medium"],
        "tone_preferences": ["technical", "visionary"]
    }
    
    print("🚀 Testing Marketing Campaign Generation via Temporal Workflow")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Create campaign
        print("\n1. Creating marketing campaign...")
        response = await client.post(
            f"{API_BASE}/campaigns",
            json=campaign_request,
            headers={
                "X-User-ID": "test-user",
                "X-Tenant-ID": "test-tenant"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create campaign: {response.text}")
            return
        
        result = response.json()
        workflow_id = result.get("workflow_id")
        print(f"✅ Campaign creation started")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Status: {result.get('status')}")
        
        # Step 2: Check workflow status
        if workflow_id:
            print("\n2. Checking workflow status...")
            await asyncio.sleep(5)  # Give workflow time to start
            
            status_response = await client.get(
                f"{API_BASE}/workflows/{workflow_id}",
                headers={
                    "X-User-ID": "test-user",
                    "X-Tenant-ID": "test-tenant"
                }
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"✅ Workflow Status: {status.get('status')}")
                print(f"   Start Time: {status.get('start_time')}")
                print(f"   Task Queue: {status.get('task_queue')}")
        
        # Step 3: Test content generation
        print("\n3. Testing individual content generation...")
        content_request = {
            "content_type": "tweet_thread",
            "channel": "twitter",
            "tone": "technical",
            "topic": "AI-powered development platform launch"
        }
        
        content_response = await client.post(
            f"{API_BASE}/content/generate",
            json=content_request,
            headers={
                "X-User-ID": "test-user",
                "X-Tenant-ID": "test-tenant"
            }
        )
        
        if content_response.status_code == 200:
            content = content_response.json()
            print("✅ Content generated successfully")
            print(f"   Content ID: {content.get('content_id')}")
            print(f"   Type: {content.get('type')}")
            print(f"   Channel: {content.get('channel')}")
        else:
            print(f"❌ Content generation failed: {content_response.text}")
        
        # Step 4: Test campaign optimization
        if result.get("campaign_id"):
            print("\n4. Testing campaign optimization...")
            opt_response = await client.post(
                f"{API_BASE}/campaigns/{result['campaign_id']}/optimize",
                headers={
                    "X-User-ID": "test-user",
                    "X-Tenant-ID": "test-tenant"
                }
            )
            
            if opt_response.status_code == 200:
                optimization = opt_response.json()
                print("✅ Campaign optimization initiated")
                print(f"   Optimization Workflow: {optimization.get('workflow_id')}")
            else:
                print(f"❌ Optimization failed: {opt_response.text}")


async def test_workflow_endpoints():
    """Test the workflow support endpoints directly"""
    
    print("\n\n🔧 Testing Workflow Support Endpoints")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test strategy generation
        print("\n1. Testing strategy generation endpoint...")
        strategy_request = {
            "objective": "technical_evangelism",
            "product_description": "Revolutionary AI platform",
            "key_features": ["AI-powered", "Fast", "Reliable"],
            "target_audience": "Developers",
            "unique_value_prop": "10x faster development",
            "duration_days": 30,
            "channels": ["twitter", "devto"]
        }
        
        response = await client.post(
            f"{BASE_URL}/marketing/strategy",
            json=strategy_request
        )
        
        if response.status_code == 200:
            print("✅ Strategy generation successful")
            strategy = response.json()
            print(f"   Themes: {strategy.get('content_themes')}")
            print(f"   Pillars: {strategy.get('messaging_pillars')}")
        else:
            print(f"❌ Strategy generation failed: {response.text}")
        
        # Test calendar creation
        print("\n2. Testing calendar creation endpoint...")
        calendar_request = {
            "duration_days": 7,
            "channels": ["twitter", "linkedin"],
            "strategy": {"key": "test"},
            "launch_date": datetime.now().isoformat()
        }
        
        response = await client.post(
            f"{BASE_URL}/marketing/calendar",
            json=calendar_request
        )
        
        if response.status_code == 200:
            print("✅ Calendar creation successful")
            calendar = response.json()
            print(f"   Days scheduled: {len(calendar.get('calendar', {}))}")
        else:
            print(f"❌ Calendar creation failed: {response.text}")


async def main():
    """Run all tests"""
    print("🎯 Marketing Workflow Integration Tests")
    print("=" * 80)
    print("Ensure the following services are running:")
    print("- Orchestrator (port 8000)")
    print("- Temporal server")
    print("- Marketing workflow worker")
    print("=" * 80)
    
    try:
        # Run tests
        await test_campaign_generation()
        await test_workflow_endpoints()
        
        print("\n\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())