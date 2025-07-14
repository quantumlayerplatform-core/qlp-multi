#!/usr/bin/env python3
"""
Test script for marketing workflow with auto-publishing
"""

import requests
import json
import time

def test_marketing_with_auto_publish():
    """Test marketing campaign with auto-publishing enabled"""
    
    # Test endpoint URL
    url = "http://localhost:8000/test-marketing-no-auth"
    
    # Campaign data with auto-publish enabled
    campaign_data = {
        "objective": "launch_awareness",
        "product_description": "Revolutionary AI-powered platform that transforms software development",
        "key_features": [
            "AI automation",
            "No-code development", 
            "Enterprise ready",
            "Replace entire dev teams"
        ],
        "target_audience": "CTOs and technical decision makers",
        "unique_value_prop": "Replace entire dev teams with AI",
        "duration_days": 3,  # Shorter for testing
        "channels": ["twitter", "linkedin"],
        "tone_preferences": ["technical", "visionary"],
        "auto_publish": True,  # Enable auto-publishing
        "publish_immediately": True  # Publish as soon as generated
    }
    
    print("🚀 Starting marketing campaign with auto-publishing...")
    print(json.dumps(campaign_data, indent=2))
    
    try:
        # Send request
        response = requests.post(url, json=campaign_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Campaign started successfully!")
            print(f"Workflow ID: {result['workflow_id']}")
            print(f"Status: {result['status']}")
            
            # Get workflow status endpoint
            workflow_id = result['workflow_id']
            status_url = f"http://localhost:8000/api/v2/marketing/workflows/{workflow_id}"
            
            print("\n⏳ Monitoring workflow progress...")
            
            # Poll for completion
            max_attempts = 60  # 5 minutes max
            for i in range(max_attempts):
                time.sleep(5)  # Check every 5 seconds
                
                # Note: This endpoint requires auth, so we'll check logs instead
                print(f"Check {i+1}/{max_attempts} - View Temporal UI or logs for status")
                
        else:
            print(f"\n❌ Failed to start campaign: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def check_publishing_config():
    """Check if social media publishing is configured"""
    
    print("\n📋 Checking publishing configuration...")
    
    # Check environment variables
    import os
    
    twitter_configured = all([
        os.getenv('TWITTER_API_KEY'),
        os.getenv('TWITTER_API_SECRET'),
        os.getenv('TWITTER_ACCESS_TOKEN'),
        os.getenv('TWITTER_ACCESS_SECRET')
    ])
    
    linkedin_configured = all([
        os.getenv('LINKEDIN_EMAIL'),
        os.getenv('LINKEDIN_PASSWORD')
    ])
    
    print(f"Twitter configured: {'✅' if twitter_configured else '❌'}")
    print(f"LinkedIn configured: {'✅' if linkedin_configured else '❌'}")
    
    if not twitter_configured and not linkedin_configured:
        print("\n⚠️  No social media platforms configured for auto-publishing")
        print("To enable auto-publishing, set the following environment variables:")
        print("\nFor Twitter:")
        print("  - TWITTER_API_KEY")
        print("  - TWITTER_API_SECRET")
        print("  - TWITTER_ACCESS_TOKEN")
        print("  - TWITTER_ACCESS_SECRET")
        print("\nFor LinkedIn:")
        print("  - LINKEDIN_EMAIL")
        print("  - LINKEDIN_PASSWORD")
    
    return twitter_configured or linkedin_configured


if __name__ == "__main__":
    print("🔧 Marketing Auto-Publishing Test")
    print("=" * 50)
    
    # Check configuration first
    configured = check_publishing_config()
    
    if configured:
        # Run the test
        test_marketing_with_auto_publish()
    else:
        print("\n🔔 Running campaign generation only (no auto-publishing)")
        test_marketing_with_auto_publish()
    
    print("\n📊 To view results:")
    print("1. Check Temporal UI: http://localhost:8088")
    print("2. View logs: docker logs qlp-marketing-worker -f")