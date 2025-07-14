#!/usr/bin/env python3
"""
Direct test of AWS Bedrock client
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_direct():
    """Test AWS Bedrock directly through the platform"""
    from src.agents.azure_llm_client import llm_client, LLMProvider, get_model_for_tier
    from src.common.config import settings
    
    print("🧪 Direct AWS Bedrock Test")
    print("=" * 60)
    
    # Show configuration
    print(f"AWS Region: {settings.AWS_REGION}")
    print(f"AWS Credentials: {'✅ Configured' if settings.AWS_ACCESS_KEY_ID else '❌ Missing'}")
    print(f"Available providers: {llm_client.get_available_providers()}")
    print()
    
    # Check tier mapping
    print("Tier Mapping:")
    for tier in ['T0', 'T1', 'T2', 'T3']:
        model, provider = get_model_for_tier(tier)
        print(f"  {tier}: {model} via {provider.value}")
    print()
    
    # Test AWS Bedrock directly
    if 'aws_bedrock' in llm_client.get_available_providers():
        print("Testing AWS Bedrock Claude 3 Haiku...")
        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": "Say 'Hello from AWS Bedrock!' and nothing else."}],
                model=settings.AWS_T0_MODEL,
                provider=LLMProvider.AWS_BEDROCK,
                max_tokens=50,
                temperature=0.1,
                use_optimized=False  # Force direct AWS Bedrock
            )
            
            print(f"✅ Success!")
            print(f"Response: {response['content']}")
            print(f"Provider: {response['provider']}")
            print(f"Model: {response['model']}")
            print(f"Region: {response.get('region', 'N/A')}")
            print(f"Latency: {response['latency']:.2f}s")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ AWS Bedrock not available")

if __name__ == "__main__":
    asyncio.run(test_direct())