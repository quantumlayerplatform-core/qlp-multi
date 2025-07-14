#!/usr/bin/env python3
"""
Simple AWS Bedrock Integration Test
Quick test to verify AWS Bedrock is working
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_bedrock():
    """Simple test of AWS Bedrock integration"""
    try:
        from src.common.config import settings
        from src.agents.azure_llm_client import llm_client, LLMProvider, get_model_for_tier
        
        print("🔍 AWS Bedrock Integration Test")
        print("=" * 50)
        
        # Check configuration
        print(f"✓ AWS Region: {settings.AWS_REGION}")
        print(f"✓ Credentials configured: {bool(settings.AWS_ACCESS_KEY_ID)}")
        
        # Check provider availability
        providers = llm_client.get_available_providers()
        print(f"✓ Available providers: {providers}")
        
        bedrock_available = "aws_bedrock" in providers
        print(f"✓ AWS Bedrock available: {bedrock_available}")
        
        if not bedrock_available:
            print("\n❌ AWS Bedrock not available. Please check:")
            print("1. AWS credentials are set in .env")
            print("2. boto3 is installed: pip install boto3")
            return
        
        # Test tier mapping
        print("\n📊 Tier Mapping:")
        for tier in ["T0", "T1", "T2", "T3"]:
            model, provider = get_model_for_tier(tier)
            print(f"  {tier}: {model} via {provider.value}")
        
        # Test a simple completion
        print("\n🤖 Testing Claude via AWS Bedrock...")
        
        test_prompt = "Complete this Python function:\ndef fibonacci(n):\n    # Returns the nth Fibonacci number"
        
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": test_prompt}],
            model=settings.AWS_T2_MODEL,  # Use T2 for code generation
            provider=LLMProvider.AWS_BEDROCK,
            max_tokens=200,
            temperature=0.3
        )
        
        print(f"\n✅ Success! Response from {response['model']}:")
        print("-" * 50)
        print(response["content"][:500])  # First 500 chars
        print("-" * 50)
        
        # Show metrics
        print(f"\n📈 Performance Metrics:")
        print(f"  Provider: {response['provider']}")
        print(f"  Region: {response.get('region', 'N/A')}")
        print(f"  Latency: {response['latency']:.2f}s")
        print(f"  Tokens: {response['usage']['total_tokens']}")
        
        if 'cost' in response:
            cost = response['cost']
            print(f"  Cost: ${cost['total_cost_usd']:.6f}")
        
        # Get overall metrics
        metrics = llm_client.get_metrics()
        print(f"\n📊 Overall Stats:")
        print(f"  Total requests: {metrics['total_requests']}")
        print(f"  Success rate: {(1 - metrics['error_rate']) * 100:.1f}%")
        print(f"  Average latency: {metrics['average_latency']:.2f}s")
        
        print("\n🎉 AWS Bedrock integration is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials in .env")
        print("2. Ensure boto3 is installed")
        print("3. Verify AWS region supports Bedrock")
        print("4. Check IAM permissions for Bedrock access")


if __name__ == "__main__":
    print(f"Starting test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    asyncio.run(test_bedrock())