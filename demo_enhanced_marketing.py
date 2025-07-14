#!/usr/bin/env python3
"""
Demo: Enhanced Marketing System with Advanced Agents

Shows the complete AI-powered marketing campaign system in action.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from src.agents.marketing import (
    MarketingOrchestrator,
    ThreadBuilderAgent,
    CampaignClassifierAgent,
    PersonaAgent,
    ABTestingAgent,
    FeedbackSummarizerAgent
)
from src.agents.marketing.models import (
    CampaignRequest, CampaignObjective, Channel, 
    ContentType, ToneStyle, MarketingContent,
    ContentPerformance, CampaignAnalytics
)
from src.common.marketing_capsule import MarketingCapsule


async def demo_thread_builder():
    """Demo: ThreadBuilderAgent creating viral Twitter threads"""
    print("\n" + "="*60)
    print("🧵 DEMO: Thread Builder Agent")
    print("="*60)
    
    agent = ThreadBuilderAgent()
    
    # Build educational thread
    thread = await agent.build_thread(
        topic="How AI agents are revolutionizing software development",
        key_points=[
            "Traditional development takes months",
            "AI agents work like senior developers",
            "Pattern recognition reduces compute by 60%",
            "Real production code, not prototypes",
            "Continuous learning from every execution"
        ],
        pattern="educational",
        target_audience="developers",
        include_media=True
    )
    
    print(f"\n📝 Generated {len(thread['tweets'])} tweets:")
    for i, tweet in enumerate(thread['tweets']):
        print(f"\n{tweet}")
    
    print(f"\n📊 Thread Metadata:")
    print(f"- Pattern: {thread['pattern']}")
    print(f"- Estimated read time: {thread['estimated_read_time']}s")
    print(f"- Optimal posting: {thread['optimal_posting_time']}")
    print(f"- Suggested hashtags: {', '.join(thread['hashtag_suggestions'])}")
    
    # Show media suggestions
    print(f"\n🖼️ Media Suggestions:")
    for media in thread['media_suggestions'][:3]:
        print(f"- Tweet {media['tweet_index']+1}: {media['description']}")


async def demo_campaign_classifier():
    """Demo: CampaignClassifierAgent analyzing campaigns"""
    print("\n" + "="*60)
    print("🗂️ DEMO: Campaign Classifier Agent")
    print("="*60)
    
    agent = CampaignClassifierAgent()
    
    # Create sample campaign for analysis
    campaign = MarketingCampaign(
        objective=CampaignObjective.LAUNCH_AWARENESS,
        target_audience="CTOs and Engineering Leaders",
        duration_days=30,
        content_pieces=[
            MarketingContent(
                type=ContentType.LINKEDIN_POST,
                channel=Channel.LINKEDIN,
                content="After 20 years in tech, I've learned one thing...",
                tone=ToneStyle.VISIONARY,
                target_audience="CTOs"
            ),
            MarketingContent(
                type=ContentType.TWEET_THREAD,
                channel=Channel.TWITTER,
                content="🚀 We just shipped v2.0. Here's what we learned...",
                tone=ToneStyle.EDUCATIONAL,
                target_audience="Developers"
            ),
            # Add more sample content...
        ],
        content_calendar={},
        strategy_summary="Launch awareness campaign"
    )
    
    # Classify campaign
    classification = await agent.classify_campaign(campaign)
    
    print(f"\n📊 Campaign Classification:")
    print(f"- Primary Format: {classification['classifications']['primary_format']}")
    print(f"- Primary Tone: {classification['classifications']['primary_tone']}")
    print(f"- CTA Effectiveness: {classification['classifications']['cta_effectiveness_score']:.1%}")
    
    print(f"\n💡 Key Insights:")
    for insight_type, insights in classification['insights'].items():
        if insights:
            print(f"\n{insight_type.replace('_', ' ').title()}:")
            if isinstance(insights, list):
                for insight in insights[:2]:
                    print(f"  - {insight}")
            else:
                print(f"  - {insights}")
    
    print(f"\n🎯 Predicted Performance: {classification['predicted_performance']['overall_score']:.1%}")
    print(f"Engagement Level: {classification['predicted_performance']['engagement_prediction']}")


async def demo_persona_variants():
    """Demo: PersonaAgent creating targeted content"""
    print("\n" + "="*60)
    print("🧬 DEMO: Persona Agent")
    print("="*60)
    
    agent = PersonaAgent()
    
    # Original content
    original = """
    QuantumLayer transforms how teams build software. Our AI agents generate 
    production-ready code in hours instead of months, with enterprise-grade 
    quality and security built in.
    """
    
    # Generate variants for different personas
    personas = ["cto", "engineering_lead", "startup_founder", "developer"]
    
    print(f"\n📝 Original Content:")
    print(original)
    
    for persona in personas:
        variant = await agent.create_persona_variant(
            original_content=original,
            target_persona=persona,
            content_type="linkedin_post"
        )
        
        print(f"\n👤 {persona.upper()} Variant:")
        print(variant['content'])
        print(f"\nKey Adjustments: {', '.join(variant['key_adjustments'])}")
        print(f"Recommended Channels: {', '.join(variant['recommended_channels'][:2])}")


async def demo_ab_testing():
    """Demo: ABTestingAgent running tests"""
    print("\n" + "="*60)
    print("🧪 DEMO: A/B Testing Agent")
    print("="*60)
    
    agent = ABTestingAgent()
    
    # Create test content
    original = MarketingContent(
        type=ContentType.LINKEDIN_POST,
        channel=Channel.LINKEDIN,
        content="Build software 10x faster with AI agents",
        title="The Future of Development",
        cta="Learn More",
        tone=ToneStyle.VISIONARY,
        target_audience="CTOs"
    )
    
    # Define variants
    variants = [
        {
            "title": "Your Competition is Using AI. Are You?",
            "cta": "Start Free Trial",
            "modifications": ["Urgency-based title", "Direct CTA"]
        },
        {
            "content": "What if your team could ship in hours, not months?",
            "cta": "See Live Demo",
            "modifications": ["Question hook", "Demo CTA"]
        }
    ]
    
    # Create A/B test
    test = await agent.create_ab_test(
        original_content=original,
        test_name="LinkedIn Hook Test",
        variants=variants,
        test_duration_hours=48
    )
    
    print(f"\n🧪 A/B Test Created:")
    print(f"- Test ID: {test['test_id']}")
    print(f"- Variants: {test['variants_count']} (including control)")
    print(f"- Duration: {test['duration_hours']} hours")
    
    # Simulate performance data
    print(f"\n📊 Simulating Performance...")
    
    # Control performance
    await agent.track_performance(
        test['test_id'], "control",
        {"impressions": 1000, "clicks": 50, "conversions": 5}
    )
    
    # Variant 1 performance (winner)
    await agent.track_performance(
        test['test_id'], "variant_1",
        {"impressions": 1000, "clicks": 80, "conversions": 12}
    )
    
    # Variant 2 performance
    await agent.track_performance(
        test['test_id'], "variant_2",
        {"impressions": 1000, "clicks": 65, "conversions": 8}
    )
    
    # Get results
    results = await agent.conclude_test(test['test_id'])
    
    print(f"\n🏆 Test Results:")
    print(f"- Winner: {results['winner']}")
    print(f"- Lift: {results['lift']}")
    print(f"- Reason: {results['reason']}")
    
    print(f"\n💡 Recommendations:")
    for rec in results['recommendations'][:3]:
        print(f"- {rec}")


async def demo_feedback_summarizer():
    """Demo: FeedbackSummarizerAgent creating briefs"""
    print("\n" + "="*60)
    print("🧠 DEMO: Feedback Summarizer Agent")
    print("="*60)
    
    agent = FeedbackSummarizerAgent()
    
    # Create sample analytics
    analytics = CampaignAnalytics(
        campaign_id="campaign_123",
        total_impressions=50000,
        total_clicks=2500,
        total_conversions=125,
        avg_engagement_rate=0.05,
        best_performing_content=["content_1", "content_3", "content_7"],
        worst_performing_content=["content_12", "content_15"],
        channel_performance={
            "twitter": {
                "total_impressions": 20000,
                "avg_engagement_rate": 0.06,
                "click_rate": 0.04
            },
            "linkedin": {
                "total_impressions": 30000,
                "avg_engagement_rate": 0.04,
                "click_rate": 0.03
            }
        },
        recommendations=[
            "Focus on Twitter for higher engagement",
            "Test video content on LinkedIn",
            "Increase posting frequency"
        ]
    )
    
    # Create campaign brief
    brief = await agent.create_campaign_brief(analytics)
    
    print(f"\n📋 3-Bullet Campaign Brief:")
    for i, bullet in enumerate(brief['brief_bullets'], 1):
        print(f"{i}. {bullet}")
    
    print(f"\n🎯 Performance Tier: {brief['performance_tier']}")
    
    print(f"\n📊 Next Campaign Strategy:")
    strategy = brief['next_campaign_strategy']
    print(f"- Focus: {strategy['strategy_focus']}")
    print(f"- Budget: {strategy['budget_recommendation']}")
    print(f"- Expected Improvement: {strategy['expected_improvement']}")
    
    print(f"\n🧪 Testing Priorities:")
    for priority in strategy['testing_priorities'][:2]:
        print(f"- {priority['test']}: {priority['hypothesis']}")


async def demo_integrated_campaign():
    """Demo: Complete integrated campaign with all agents"""
    print("\n" + "="*60)
    print("🚀 DEMO: Integrated Marketing Campaign")
    print("="*60)
    
    # Initialize orchestrator with enhanced agents
    orchestrator = MarketingOrchestrator()
    
    # Create campaign request
    request = CampaignRequest(
        objective=CampaignObjective.LAUNCH_AWARENESS,
        product_description="QuantumLayer - AI agents that build production software",
        key_features=[
            "Multi-tier AI agents optimized for cost/quality",
            "60-70% compute reduction with pattern selection",
            "Production-ready code with 5-stage validation",
            "Continuous learning from every execution"
        ],
        target_audience="CTOs, Engineering Leaders, and Senior Developers",
        unique_value_prop="Build production software in hours, not months",
        duration_days=30,
        channels=[Channel.TWITTER, Channel.LINKEDIN, Channel.EMAIL],
        tone_preferences=[ToneStyle.VISIONARY, ToneStyle.TECHNICAL]
    )
    
    print("\n📅 Generating Complete Campaign...")
    campaign = await orchestrator.generate_campaign(request)
    
    print(f"\n✅ Campaign Generated!")
    print(f"- Campaign ID: {campaign.campaign_id}")
    print(f"- Total Content: {campaign.total_pieces} pieces")
    print(f"- Channels: {', '.join(c.value for c in campaign.channels_used)}")
    
    # Create marketing capsule
    capsule = MarketingCapsule(
        request_id=f"demo_{datetime.now().timestamp()}",
        user_id="demo_user",
        tenant_id="demo_tenant",
        campaign_data=campaign
    )
    
    print(f"\n📦 Marketing Capsule Created!")
    print(f"- Capsule ID: {capsule.capsule_id}")
    print(f"- Export formats available: ZIP, JSON, Markdown, Buffer, Hootsuite")
    
    # Show sample content
    print(f"\n📝 Sample Content Pieces:")
    for content in campaign.content_pieces[:3]:
        print(f"\n[{content.channel.value.upper()}] {content.type.value}")
        print(f"Content: {content.content[:150]}...")
        if content.cta:
            print(f"CTA: {content.cta}")


async def main():
    """Run all demos"""
    print("🎯 QuantumLayer Enhanced Marketing System Demo")
    print("=" * 80)
    
    demos = [
        ("Thread Builder", demo_thread_builder),
        ("Campaign Classifier", demo_campaign_classifier),
        ("Persona Variants", demo_persona_variants),
        ("A/B Testing", demo_ab_testing),
        ("Feedback Summarizer", demo_feedback_summarizer),
        ("Integrated Campaign", demo_integrated_campaign)
    ]
    
    for name, demo_func in demos:
        try:
            await demo_func()
            await asyncio.sleep(1)  # Brief pause between demos
        except Exception as e:
            print(f"\n❌ Error in {name} demo: {e}")
    
    print("\n" + "="*80)
    print("✅ Enhanced Marketing System Demo Complete!")
    print("\nThe AI-powered marketing system is ready to:")
    print("- 🧵 Build viral thread narratives")
    print("- 🗂️ Classify and analyze campaigns")
    print("- 🧬 Create persona-specific variants")
    print("- 🧪 Run sophisticated A/B tests")
    print("- 🧠 Generate actionable campaign briefs")
    print("- 🚀 Orchestrate complete marketing campaigns")


if __name__ == "__main__":
    # Note: This is a demo script. In production, you would need:
    # 1. Valid API keys for OpenAI/Anthropic
    # 2. Database connections
    # 3. Redis for caching
    # 4. Actual content performance data
    
    # For demo purposes, we'll show the structure and capabilities
    print("\n⚠️  Note: This demo shows the system structure.")
    print("In production, it would generate real content using LLMs.")
    
    # Run async demo
    # asyncio.run(main())
    
    # For now, just show what's available
    print("\n📚 Enhanced Marketing Agents Available:")
    print("1. ThreadBuilderAgent - Creates multi-tweet narratives")
    print("2. CampaignClassifierAgent - Analyzes campaign patterns")
    print("3. PersonaAgent - Crafts persona-specific messaging")
    print("4. ABTestingAgent - Manages content experiments")
    print("5. FeedbackSummarizerAgent - Creates actionable briefs")
    
    print("\n🔧 To run the full demo:")
    print("1. Ensure API keys are configured")
    print("2. Start Docker services")
    print("3. Uncomment asyncio.run(main())")
    print("4. Run: python demo_enhanced_marketing.py")