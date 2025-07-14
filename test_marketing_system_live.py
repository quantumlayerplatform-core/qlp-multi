#!/usr/bin/env python3
"""
Test Enhanced Marketing System via API

This script demonstrates the marketing system through API calls.
"""

import requests
import json
import time
from datetime import datetime


BASE_URL = "http://localhost:8000"
MARKETING_API = f"{BASE_URL}/api/v2/marketing"


def test_create_campaign():
    """Test creating a marketing campaign"""
    print("\n" + "="*60)
    print("🚀 TEST: Create Marketing Campaign")
    print("="*60)
    
    campaign_request = {
        "objective": "launch_awareness",
        "product_description": "QuantumLayer - AI agents that build production-ready software in hours instead of months",
        "key_features": [
            "Multi-tier AI agents (T0-T3) optimized for cost and quality",
            "Pattern Selection Engine with 60-70% compute reduction",
            "Temporal workflows for reliable execution",
            "Qdrant vector memory for continuous learning",
            "5-stage validation ensuring production quality"
        ],
        "target_audience": "CTOs, Engineering Leaders, and Senior Developers at scaling startups",
        "unique_value_prop": "Build production software 100x faster with AI agents that think like senior developers",
        "duration_days": 30,
        "channels": ["twitter", "linkedin", "email"],
        "tone_preferences": ["technical", "visionary"]
    }
    
    print("\n📋 Campaign Request:")
    print(f"- Objective: {campaign_request['objective']}")
    print(f"- Target: {campaign_request['target_audience']}")
    print(f"- Duration: {campaign_request['duration_days']} days")
    print(f"- Channels: {', '.join(campaign_request['channels'])}")
    
    try:
        response = requests.post(
            f"{MARKETING_API}/campaigns",
            json=campaign_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Campaign Created Successfully!")
            print(f"- Campaign ID: {result['campaign_id']}")
            print(f"- Total Content: {result['total_content']} pieces")
            print(f"- Channels Used: {', '.join(result['channels'])}")
            return result['campaign_id']
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"\n❌ Error creating campaign: {e}")
        return None


def test_generate_content():
    """Test generating individual content pieces"""
    print("\n" + "="*60)
    print("📝 TEST: Generate Individual Content")
    print("="*60)
    
    # Test 1: Twitter Thread
    print("\n1️⃣ Generating Twitter Thread...")
    twitter_params = {
        "content_type": "tweet_thread",
        "channel": "twitter",
        "tone": "technical",
        "topic": "How QuantumLayer's Pattern Selection Engine reduces compute by 60%"
    }
    
    try:
        response = requests.post(
            f"{MARKETING_API}/content/generate",
            params=twitter_params
        )
        
        if response.status_code == 200:
            content = response.json()
            print("✅ Twitter Thread Generated!")
            if isinstance(content['content'], dict) and 'tweets' in content['content']:
                for i, tweet in enumerate(content['content']['tweets'][:3]):
                    print(f"\nTweet {i+1}: {tweet}")
            else:
                print(f"\nContent Preview: {str(content['content'])[:200]}...")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: LinkedIn Post
    print("\n\n2️⃣ Generating LinkedIn Post...")
    linkedin_params = {
        "content_type": "linkedin_post",
        "channel": "linkedin",
        "tone": "visionary",
        "topic": "The future of software development with AI agents"
    }
    
    try:
        response = requests.post(
            f"{MARKETING_API}/content/generate",
            params=linkedin_params
        )
        
        if response.status_code == 200:
            content = response.json()
            print("✅ LinkedIn Post Generated!")
            if isinstance(content['content'], dict):
                print(f"\nTitle: {content['content'].get('title', 'N/A')}")
                print(f"Content: {content['content'].get('content', str(content['content']))[:300]}...")
                if content['content'].get('hashtags'):
                    print(f"Hashtags: {' '.join(content['content']['hashtags'])}")
            else:
                print(f"\nContent: {str(content['content'])[:300]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")


def test_export_campaign(campaign_id):
    """Test exporting campaign in different formats"""
    print("\n" + "="*60)
    print("📦 TEST: Export Campaign")
    print("="*60)
    
    if not campaign_id:
        print("⚠️  No campaign ID available for export")
        return
    
    # Test JSON export
    print("\n📄 Exporting as JSON...")
    try:
        response = requests.post(
            f"{MARKETING_API}/campaigns/{campaign_id}/export",
            params={"format": "json"}
        )
        
        if response.status_code == 200:
            print("✅ JSON Export successful!")
            campaign_data = response.json()
            print(f"- Campaign Objective: {campaign_data.get('objective', 'N/A')}")
            print(f"- Total Pieces: {campaign_data.get('total_pieces', 0)}")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_campaign_analytics(campaign_id):
    """Test campaign analytics and recommendations"""
    print("\n" + "="*60)
    print("📊 TEST: Campaign Analytics")
    print("="*60)
    
    if not campaign_id:
        # Use a dummy campaign ID for demo
        campaign_id = "demo_campaign"
    
    try:
        response = requests.get(
            f"{MARKETING_API}/campaigns/{campaign_id}/analytics"
        )
        
        if response.status_code == 200:
            data = response.json()
            analytics = data.get('analytics', {})
            
            print("\n📈 Campaign Performance:")
            print(f"- Total Impressions: {analytics.get('total_impressions', 0):,}")
            print(f"- Total Clicks: {analytics.get('total_clicks', 0):,}")
            print(f"- Avg Engagement: {analytics.get('avg_engagement_rate', 0):.2%}")
            
            if data.get('improvements'):
                print("\n💡 Improvement Suggestions:")
                for improvement in data['improvements'][:3]:
                    if isinstance(improvement, dict):
                        print(f"- {improvement.get('type', 'General')}: {improvement.get('suggestions', ['N/A'])[0]}")
                    else:
                        print(f"- {improvement}")
                        
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_templates():
    """Test retrieving campaign templates"""
    print("\n" + "="*60)
    print("📚 TEST: Campaign Templates")
    print("="*60)
    
    try:
        response = requests.get(f"{MARKETING_API}/templates")
        
        if response.status_code == 200:
            templates = response.json().get('templates', [])
            print(f"\n✅ Found {len(templates)} templates:")
            
            for template in templates:
                print(f"\n📋 {template['name']}")
                print(f"   {template['description']}")
                print(f"   Duration: {template['duration_days']} days")
                print(f"   Channels: {', '.join(template['channels'])}")
                
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all marketing system tests"""
    print("🎯 QuantumLayer Enhanced Marketing System - Live Test")
    print("=" * 80)
    
    # Check if services are running
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ Services not responding. Please ensure Docker Compose is running:")
            print("   docker-compose -f docker-compose.platform.yml up -d")
            return
    except:
        print("❌ Cannot connect to services. Please start the platform:")
        print("   ./start.sh")
        return
    
    print("✅ Services are running!")
    
    # Run tests
    print("\nRunning marketing system tests...")
    
    # Test 1: Create campaign
    campaign_id = test_create_campaign()
    time.sleep(2)
    
    # Test 2: Generate individual content
    test_generate_content()
    time.sleep(1)
    
    # Test 3: Export campaign
    if campaign_id:
        test_export_campaign(campaign_id)
        time.sleep(1)
    
    # Test 4: Analytics
    test_campaign_analytics(campaign_id)
    time.sleep(1)
    
    # Test 5: Templates
    test_templates()
    
    print("\n" + "="*80)
    print("✅ Marketing System Test Complete!")
    print("\nThe enhanced marketing system provides:")
    print("- 🚀 Complete campaign generation")
    print("- 📝 Individual content creation")
    print("- 📊 Analytics and insights")
    print("- 📦 Multi-format exports")
    print("- 📚 Template library")
    
    print("\n💡 Next Steps:")
    print("1. Check generated content quality")
    print("2. Test A/B testing features")
    print("3. Try persona-specific variants")
    print("4. Export and schedule content")


if __name__ == "__main__":
    main()