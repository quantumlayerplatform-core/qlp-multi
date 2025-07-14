#!/usr/bin/env python3
"""
Test script for HAP (Hate, Abuse, Profanity) detection system
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any

from src.moderation import (
    hap_service, check_content, 
    CheckContext, Severity, Category
)


# Test cases with expected results
TEST_CASES = [
    # Clean content
    {
        "content": "Please write a Python function to calculate fibonacci numbers",
        "expected_severity": Severity.CLEAN,
        "description": "Clean technical request"
    },
    {
        "content": "Create a REST API endpoint for user authentication",
        "expected_severity": Severity.CLEAN,
        "description": "Clean development task"
    },
    
    # Mild profanity
    {
        "content": "This damn code doesn't work, fix it",
        "expected_severity": Severity.LOW,
        "description": "Mild profanity"
    },
    {
        "content": "What the hell is wrong with this function?",
        "expected_severity": Severity.LOW,
        "description": "Mild profanity in frustration"
    },
    
    # Abuse/threats
    {
        "content": "I will hurt anyone who uses tabs instead of spaces",
        "expected_severity": Severity.HIGH,
        "description": "Threat of violence (even if joking)"
    },
    
    # Technical edge cases
    {
        "content": "The kill command terminates processes in Unix",
        "expected_severity": Severity.CLEAN,
        "description": "Technical term that could be misidentified"
    },
    {
        "content": "Use git push --force to override remote",
        "expected_severity": Severity.CLEAN,
        "description": "Technical command with 'force'"
    },
    
    # Disguised profanity
    {
        "content": "This code is f*cking broken",
        "expected_severity": Severity.MEDIUM,
        "description": "Disguised profanity"
    },
    {
        "content": "Fix this sh!t ASAP",
        "expected_severity": Severity.MEDIUM,
        "description": "Leetspeak profanity"
    }
]


async def test_individual_checks():
    """Test individual content checks"""
    print("=== Individual Content Checks ===\n")
    
    # Initialize service
    await hap_service.initialize()
    
    results = []
    for i, test_case in enumerate(TEST_CASES):
        print(f"Test {i+1}: {test_case['description']}")
        print(f"Content: '{test_case['content']}'")
        
        # Perform check
        result = await check_content(
            content=test_case['content'],
            context=CheckContext.USER_REQUEST,
            user_id="test_user",
            tenant_id="test_tenant"
        )
        
        # Display result
        print(f"Result: {result.result}")
        print(f"Severity: {result.severity} (expected: {test_case['expected_severity']})")
        print(f"Categories: {[cat.value for cat in result.categories]}")
        print(f"Confidence: {result.confidence:.2f}")
        if result.explanation:
            print(f"Explanation: {result.explanation}")
        if result.suggestions:
            print(f"Suggestions: {result.suggestions}")
        print(f"Processing time: {result.processing_time_ms:.2f}ms")
        
        # Check if matches expectation
        matches = result.severity == test_case['expected_severity']
        print(f"✓ PASS" if matches else f"✗ FAIL")
        print("-" * 50)
        
        results.append({
            "test": test_case['description'],
            "passed": matches,
            "severity": result.severity,
            "expected": test_case['expected_severity']
        })
    
    # Summary
    passed = sum(1 for r in results if r['passed'])
    print(f"\nSummary: {passed}/{len(results)} tests passed")
    
    return results


async def test_batch_processing():
    """Test batch content checking"""
    print("\n=== Batch Processing Test ===\n")
    
    # Prepare batch
    batch_content = [
        "Write a function to sort an array",
        "This damn bug is annoying",
        "Implement user authentication",
        "Fix this sh*t before deadline"
    ]
    
    print(f"Processing {len(batch_content)} items in batch...")
    start_time = asyncio.get_event_loop().time()
    
    # Process batch
    tasks = [
        check_content(content, context=CheckContext.USER_REQUEST)
        for content in batch_content
    ]
    results = await asyncio.gather(*tasks)
    
    end_time = asyncio.get_event_loop().time()
    total_time = (end_time - start_time) * 1000
    
    # Display results
    for i, (content, result) in enumerate(zip(batch_content, results)):
        print(f"{i+1}. '{content[:50]}...' -> {result.severity}")
    
    print(f"\nTotal batch processing time: {total_time:.2f}ms")
    print(f"Average per item: {total_time/len(batch_content):.2f}ms")


async def test_cache_performance():
    """Test caching performance"""
    print("\n=== Cache Performance Test ===\n")
    
    test_content = "Check if this content is cached properly"
    
    # First check (cache miss)
    start = asyncio.get_event_loop().time()
    result1 = await check_content(test_content)
    time1 = (asyncio.get_event_loop().time() - start) * 1000
    
    # Second check (cache hit)
    start = asyncio.get_event_loop().time()
    result2 = await check_content(test_content)
    time2 = (asyncio.get_event_loop().time() - start) * 1000
    
    print(f"First check (cache miss): {time1:.2f}ms")
    print(f"Second check (cache hit): {time2:.2f}ms")
    print(f"Speed improvement: {time1/time2:.1f}x faster")
    print(f"Results match: {result1.severity == result2.severity}")


async def test_context_awareness():
    """Test different contexts"""
    print("\n=== Context Awareness Test ===\n")
    
    contexts = [
        CheckContext.USER_REQUEST,
        CheckContext.AGENT_OUTPUT,
        CheckContext.CAPSULE_CONTENT
    ]
    
    test_content = "Generate code to handle user input"
    
    for context in contexts:
        result = await check_content(
            content=test_content,
            context=context
        )
        print(f"Context: {context.value}")
        print(f"Severity: {result.severity}")
        print("-" * 30)


async def test_agent_integration():
    """Test HAP integration with agents"""
    print("\n=== Agent Integration Test ===\n")
    
    from src.agents.hap_filtered_agent import create_hap_filtered_agent
    from src.agents.base_agents import BaseAgent
    from src.common.models import Task, AgentType
    
    # Create mock base agent
    class MockAgent(BaseAgent):
        async def execute(self, task: Task):
            # Simulate agent generating inappropriate content
            if "bad" in task.description:
                output = "This is a damn terrible implementation"
            else:
                output = "Here's a clean implementation of your request"
            
            return type('TaskResult', (), {
                'task_id': task.task_id,
                'agent_id': self.agent_id,
                'output': output,
                'status': 'completed',
                'execution_time': 0.1,
                'metadata': {}
            })()
    
    # Create base and filtered agents
    base_agent = MockAgent(
        agent_id="mock-agent",
        agent_type=AgentType.DEVELOPER,
        tier=1
    )
    
    filtered_agent = create_hap_filtered_agent(base_agent, strict_mode=True)
    
    # Test cases
    test_tasks = [
        Task(
            task_id="test-1",
            description="Write a clean function",
            agent_type=AgentType.DEVELOPER,
            metadata={"user_id": "test_user"}
        ),
        Task(
            task_id="test-2",
            description="Fix this bad code",
            agent_type=AgentType.DEVELOPER,
            metadata={"user_id": "test_user"}
        )
    ]
    
    for task in test_tasks:
        print(f"\nTask: {task.description}")
        result = await filtered_agent.execute(task)
        print(f"Output: {result.output}")
        print(f"Filtered: {result.metadata.get('hap_filtered', False)}")


async def main():
    """Run all tests"""
    print("HAP System Test Suite")
    print("=" * 60)
    
    try:
        # Run individual tests
        await test_individual_checks()
        
        # Run performance tests
        await test_batch_processing()
        await test_cache_performance()
        
        # Run integration tests
        await test_context_awareness()
        await test_agent_integration()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())