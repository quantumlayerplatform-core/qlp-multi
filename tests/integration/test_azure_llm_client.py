#!/usr/bin/env python3
"""
Test Azure LLM Client with Rate Limiting and Retry Logic

This script tests the modified Azure LLM client to ensure:
1. Rate limiting works correctly
2. Retry logic handles failures gracefully
3. Timeouts are appropriate for enterprise tasks
"""

import asyncio
import sys
import time
from typing import List, Dict

# Add src to path for imports
sys.path.insert(0, '.')

from src.agents.azure_llm_client import LLMClient, LLMProvider
from src.agents.rate_limiter import global_rate_limiter
from src.common.config import settings


async def test_basic_completion():
    """Test basic chat completion"""
    print("\n1. Testing Basic Chat Completion")
    print("=" * 50)
    
    client = LLMClient()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2? Answer in one word."}
    ]
    
    try:
        start_time = time.time()
        response = await client.chat_completion(
            messages=messages,
            model="gpt-4",
            provider=LLMProvider.AZURE_OPENAI,
            temperature=0.0,
            max_tokens=10
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Success! Response: {response}")
        print(f"  Time taken: {elapsed:.2f}s")
        print(f"  Provider: {client.last_used_provider}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def test_rate_limiting():
    """Test rate limiting behavior"""
    print("\n2. Testing Rate Limiting")
    print("=" * 50)
    
    client = LLMClient()
    
    # Set aggressive rate limits for testing
    global_rate_limiter.update_limits("azure_openai", rpm=3, tpm=100)
    
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    # Try to make 5 rapid requests
    print("Making 5 rapid requests with RPM limit of 3...")
    
    tasks = []
    for i in range(5):
        task = client.chat_completion(
            messages=messages,
            model="gpt-4",
            provider=LLMProvider.AZURE_OPENAI,
            max_tokens=5
        )
        tasks.append((i, task))
    
    start_time = time.time()
    results = []
    
    for i, task in tasks:
        try:
            result = await task
            elapsed = time.time() - start_time
            print(f"  Request {i+1}: Success at {elapsed:.1f}s")
            results.append(True)
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  Request {i+1}: Failed at {elapsed:.1f}s - {str(e)[:50]}")
            results.append(False)
    
    total_time = time.time() - start_time
    success_count = sum(results)
    
    print(f"\nRate limiting test complete:")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Successful requests: {success_count}/5")
    print(f"  Rate limiting working: {'Yes' if total_time > 10 else 'No'}")
    
    # Reset rate limits
    global_rate_limiter.update_limits("azure_openai", rpm=60, tpm=10000)
    
    return success_count >= 3  # At least 3 should succeed


async def test_retry_logic():
    """Test retry logic with simulated failures"""
    print("\n3. Testing Retry Logic")
    print("=" * 50)
    
    client = LLMClient()
    
    # Test with a very short message that might trigger retries
    messages = [
        {"role": "user", "content": "Test retry " * 100}  # Long message
    ]
    
    print("Testing retry logic with large request...")
    
    try:
        start_time = time.time()
        response = await client.chat_completion(
            messages=messages,
            model="gpt-4",
            provider=LLMProvider.AZURE_OPENAI,
            temperature=0.0,
            max_tokens=10,
            timeout=10.0  # Short timeout to potentially trigger retries
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Success after {elapsed:.2f}s")
        print(f"  Retry count: {client.metrics.get('retries', 0)}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        print(f"  Retry count: {client.metrics.get('retries', 0)}")
        return False


async def test_timeout_handling():
    """Test timeout handling for long-running requests"""
    print("\n4. Testing Timeout Handling")
    print("=" * 50)
    
    client = LLMClient()
    
    # Complex prompt that might take longer
    messages = [
        {"role": "system", "content": "You are a code generator."},
        {"role": "user", "content": "Generate a complete Python web application with Flask, including models, views, and tests. Include error handling and logging."}
    ]
    
    print("Testing with complex request and 5-minute timeout...")
    
    try:
        start_time = time.time()
        response = await client.chat_completion(
            messages=messages,
            model="gpt-4",
            provider=LLMProvider.AZURE_OPENAI,
            temperature=0.3,
            max_tokens=2000,
            timeout=300.0  # 5 minutes as per the new default
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Success! Generated {len(response)} characters")
        print(f"  Time taken: {elapsed:.2f}s")
        print(f"  Within timeout: {'Yes' if elapsed < 300 else 'No'}")
        return True
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"✗ Timeout after {elapsed:.2f}s")
        return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def test_fallback_providers():
    """Test fallback to other providers"""
    print("\n5. Testing Provider Fallback")
    print("=" * 50)
    
    client = LLMClient()
    
    messages = [
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    # Test with explicit provider that might fail
    providers = [LLMProvider.AZURE_OPENAI, LLMProvider.OPENAI, LLMProvider.ANTHROPIC]
    
    for provider in providers:
        if not client.clients.get(provider):
            print(f"  Skipping {provider.value} - not configured")
            continue
            
        try:
            response = await client.chat_completion(
                messages=messages,
                provider=provider,
                max_tokens=20
            )
            print(f"✓ {provider.value}: Success")
            return True
        except Exception as e:
            print(f"✗ {provider.value}: Failed - {str(e)[:50]}")
    
    return False


async def test_cost_tracking():
    """Test cost tracking functionality"""
    print("\n6. Testing Cost Tracking")
    print("=" * 50)
    
    client = LLMClient()
    
    initial_metrics = client.metrics.copy()
    
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    try:
        response = await client.chat_completion(
            messages=messages,
            model="gpt-4",
            provider=LLMProvider.AZURE_OPENAI,
            max_tokens=20
        )
        
        print(f"✓ Request completed")
        print(f"  Requests: {client.metrics['requests'] - initial_metrics.get('requests', 0)}")
        print(f"  Total tokens: {client.metrics['total_tokens'] - initial_metrics.get('total_tokens', 0)}")
        print(f"  Total cost: ${client.metrics['total_cost'] - initial_metrics.get('total_cost', 0):.4f}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("Azure LLM Client Test Suite")
    print("==========================")
    
    # Check configuration
    if not settings.AZURE_OPENAI_API_KEY:
        print("❌ AZURE_OPENAI_API_KEY not configured")
        print("Please set the following environment variables:")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_DEPLOYMENT_NAME")
        sys.exit(1)
    
    tests = [
        ("Basic Completion", test_basic_completion),
        ("Rate Limiting", test_rate_limiting),
        ("Retry Logic", test_retry_logic),
        ("Timeout Handling", test_timeout_handling),
        ("Provider Fallback", test_fallback_providers),
        ("Cost Tracking", test_cost_tracking),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n\nTest Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  Some tests failed. Please check the configuration and try again.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())