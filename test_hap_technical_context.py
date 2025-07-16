#!/usr/bin/env python3
"""
Test HAP Technical Context Awareness

This script tests that the HAP system correctly identifies technical context
and doesn't block programming terminology.
"""

import asyncio
import sys
from typing import List, Tuple

# Add src to path for imports
sys.path.insert(0, '.')

from src.moderation.hap_service import HAPService, HAPCheckRequest, CheckContext, Severity


async def test_technical_phrases():
    """Test common technical phrases that should NOT be blocked"""
    
    # Initialize HAP service
    hap_service = HAPService()
    await hap_service.initialize()
    
    # Test cases: (phrase, expected_max_severity)
    technical_test_cases: List[Tuple[str, Severity]] = [
        # Shell commands
        ("kill -9 12345", Severity.LOW),
        ("ps aux | grep python | kill", Severity.LOW),
        ("sudo kill the process", Severity.LOW),
        
        # Programming terminology
        ("The thread will die after timeout", Severity.LOW),
        ("Abort the transaction if error occurs", Severity.LOW),
        ("Common attack vectors in web security", Severity.LOW),
        ("The server might crash under heavy load", Severity.LOW),
        ("Destroy the object after use", Severity.LOW),
        ("Terminate the worker thread", Severity.LOW),
        ("Execute the command with sudo", Severity.CLEAN),
        
        # Code examples
        ("""
        def kill_process(pid):
            '''Kill a process by PID'''
            os.kill(pid, signal.SIGTERM)
        """, Severity.LOW),
        
        ("""
        // Handle thread termination
        if (thread.isAlive()) {
            thread.abort();  // Force kill the thread
        }
        """, Severity.LOW),
        
        # Error messages
        ("Error: Process died unexpectedly", Severity.LOW),
        ("Warning: This will destroy all data", Severity.LOW),
        
        # Documentation
        ("To kill a zombie process, use kill -9", Severity.LOW),
        ("Security: Prevent SQL injection attacks", Severity.LOW),
        
        # Variable names
        ("stupid_sort_algorithm = lambda x: sorted(x)", Severity.CLEAN),
        ("dummy_data = generate_test_data()", Severity.CLEAN),
    ]
    
    print("Testing HAP Technical Context Awareness")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for phrase, expected_max_severity in technical_test_cases:
        request = HAPCheckRequest(
            content=phrase,
            context=CheckContext.USER_REQUEST
        )
        
        result = await hap_service.check_content(request)
        
        # Check if severity is acceptable
        is_acceptable = result.severity <= expected_max_severity
        status = "✓ PASS" if is_acceptable else "✗ FAIL"
        
        if is_acceptable:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}: {phrase[:50]}...")
        print(f"  Expected max severity: {expected_max_severity.value}")
        print(f"  Actual severity: {result.severity.value}")
        print(f"  Result: {result.result}")
        if result.explanation:
            print(f"  Explanation: {result.explanation}")
    
    print("\n" + "=" * 50)
    print(f"Technical Context Tests: {passed} passed, {failed} failed")
    
    # Test non-technical harmful content (should still be blocked)
    print("\n\nTesting Non-Technical Harmful Content (Should Block)")
    print("=" * 50)
    
    harmful_test_cases = [
        ("I will kill you", Severity.HIGH),
        ("Go harm yourself", Severity.HIGH),
        ("You are so stupid and worthless", Severity.LOW),
    ]
    
    for phrase, expected_min_severity in harmful_test_cases:
        request = HAPCheckRequest(
            content=phrase,
            context=CheckContext.USER_REQUEST
        )
        
        result = await hap_service.check_content(request)
        
        # Check if severity is high enough
        is_blocked = result.severity >= expected_min_severity
        status = "✓ PASS" if is_blocked else "✗ FAIL"
        
        print(f"\n{status}: {phrase}")
        print(f"  Expected min severity: {expected_min_severity.value}")
        print(f"  Actual severity: {result.severity.value}")
        print(f"  Result: {result.result}")
    
    return passed, failed


async def test_configuration():
    """Test that configuration settings work"""
    from src.common.config import settings
    
    print("\n\nHAP Configuration Settings")
    print("=" * 50)
    print(f"HAP_ENABLED: {settings.HAP_ENABLED}")
    print(f"HAP_TECHNICAL_CONTEXT_AWARE: {settings.HAP_TECHNICAL_CONTEXT_AWARE}")
    print(f"HAP_REQUEST_BLOCKING_THRESHOLD: {settings.HAP_REQUEST_BLOCKING_THRESHOLD}")
    print(f"HAP_OUTPUT_BLOCKING_THRESHOLD: {settings.HAP_OUTPUT_BLOCKING_THRESHOLD}")
    print(f"HAP_PROFANITY_SENSITIVITY: {settings.HAP_PROFANITY_SENSITIVITY}")


async def main():
    """Run all tests"""
    
    # Test configuration
    await test_configuration()
    
    # Test technical context
    passed, failed = await test_technical_phrases()
    
    # Exit with appropriate code
    if failed > 0:
        print(f"\n❌ HAP tests failed: {failed} failures")
        sys.exit(1)
    else:
        print(f"\n✅ All HAP tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())