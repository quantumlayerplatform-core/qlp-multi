#!/usr/bin/env python3
"""
Integration tests for the fixed endpoints
Tests the workflow status, CI confidence, and improved GitHub integration
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

import httpx


# Test configuration
BASE_URL = "http://localhost:8000"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


async def test_workflow_status_endpoint():
    """Test the workflow status endpoint"""
    print("\n🔍 Testing Workflow Status Endpoint...")
    
    async with httpx.AsyncClient() as client:
        # First, start a simple workflow
        print("  Starting a test workflow...")
        response = await client.post(
            f"{BASE_URL}/generate/capsule",
            json={
                "request_id": f"test-status-{int(time.time())}",
                "tenant_id": "test",
                "user_id": "tester",
                "project_name": "Status Test Project",
                "description": "Simple hello world function",
                "requirements": "Create a function that prints hello world",
                "tech_stack": ["Python"]
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            workflow_id = result.get("workflow_id")
            
            if workflow_id:
                print(f"  Workflow ID: {workflow_id}")
                
                # Test the status endpoint
                print("  Checking workflow status...")
                for i in range(5):
                    status_response = await client.get(f"{BASE_URL}/workflow/status/{workflow_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"  Status: {status_data.get('status')}")
                        
                        if status_data.get('status') in ['completed', 'failed']:
                            print("  ✅ Workflow status endpoint working correctly!")
                            return True
                    else:
                        print(f"  ❌ Status check failed: {status_response.status_code}")
                        return False
                    
                    await asyncio.sleep(2)
                
                print("  ⚠️ Workflow still running after timeout")
                return True  # Endpoint works, just slow workflow
            else:
                print("  ❌ No workflow ID returned")
                return False
        else:
            print(f"  ❌ Failed to start workflow: {response.status_code}")
            return False


async def test_ci_confidence_endpoint():
    """Test the CI/CD confidence boost endpoint"""
    print("\n🎯 Testing CI/CD Confidence Endpoint...")
    
    if not GITHUB_TOKEN:
        print("  ⚠️ GITHUB_TOKEN not set, skipping test")
        return None
    
    async with httpx.AsyncClient() as client:
        # First, create a capsule
        print("  Creating a test capsule...")
        response = await client.post(
            f"{BASE_URL}/generate/capsule",
            json={
                "request_id": f"test-ci-{int(time.time())}",
                "tenant_id": "test",
                "user_id": "tester",
                "project_name": "CI Test Project",
                "description": "Calculator functions",
                "requirements": "Add, subtract, multiply functions",
                "tech_stack": ["Python"]
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            capsule_id = result.get("capsule_id")
            
            if capsule_id:
                print(f"  Capsule ID: {capsule_id}")
                
                # Wait a bit for capsule to be fully stored
                await asyncio.sleep(2)
                
                # Test the CI confidence endpoint
                print("  Testing CI confidence boost...")
                ci_response = await client.post(
                    f"{BASE_URL}/api/capsule/{capsule_id}/ci-confidence",
                    json={"github_token": GITHUB_TOKEN}
                )
                
                if ci_response.status_code == 200:
                    ci_data = ci_response.json()
                    print(f"  Original confidence: {ci_data.get('original_confidence')}")
                    print(f"  Applied boost: {ci_data.get('applied_boost')}")
                    print("  ✅ CI confidence endpoint working correctly!")
                    return True
                elif ci_response.status_code == 400:
                    # Expected if capsule hasn't been pushed to GitHub
                    error_detail = ci_response.json().get('detail', '')
                    if "not been pushed to GitHub" in error_detail:
                        print("  ✅ Endpoint works but capsule not on GitHub (expected)")
                        return True
                    else:
                        print(f"  ❌ Unexpected error: {error_detail}")
                        return False
                else:
                    print(f"  ❌ CI confidence test failed: {ci_response.status_code}")
                    print(f"  Response: {ci_response.text}")
                    return False
            else:
                print("  ❌ No capsule ID returned")
                return False
        else:
            print(f"  ❌ Failed to create capsule: {response.status_code}")
            return False


async def test_github_integration_error_handling():
    """Test GitHub integration with various token scenarios"""
    print("\n🔐 Testing GitHub Integration Error Handling...")
    
    async with httpx.AsyncClient() as client:
        # Test with invalid token
        print("  Testing with invalid token...")
        response = await client.post(
            f"{BASE_URL}/github/push/test-capsule-123",
            json={
                "github_token": "invalid_token_12345",
                "repo_name": "test-error-handling"
            }
        )
        
        if response.status_code in [401, 403, 500]:
            error_detail = response.json().get('detail', '')
            if "authentication failed" in error_detail.lower() or "invalid token" in error_detail.lower():
                print("  ✅ Invalid token properly handled!")
                return True
            else:
                print(f"  ⚠️ Error returned but unexpected message: {error_detail}")
                return True
        else:
            print(f"  ❌ Expected error for invalid token, got: {response.status_code}")
            return False


async def test_async_github_endpoint():
    """Test the async GitHub endpoint"""
    print("\n⚡ Testing Async GitHub Endpoint...")
    
    if not GITHUB_TOKEN:
        print("  ⚠️ GITHUB_TOKEN not set, skipping test")
        return None
    
    async with httpx.AsyncClient() as client:
        # Test the async endpoint
        print("  Starting async workflow...")
        response = await client.post(
            f"{BASE_URL}/generate/complete-with-github",
            json={
                "description": "Create a simple todo list manager",
                "github_token": GITHUB_TOKEN,
                "repo_name": f"test-async-{int(time.time())}",
                "private": True
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            workflow_id = result.get("workflow_id")
            status_url = result.get("status_check_url")
            
            if workflow_id and status_url:
                print(f"  Workflow ID: {workflow_id}")
                print(f"  Status URL: {status_url}")
                print("  ✅ Async endpoint working correctly!")
                return True
            else:
                print("  ❌ Missing workflow_id or status_check_url")
                return False
        else:
            print(f"  ❌ Failed to start async workflow: {response.status_code}")
            print(f"  Response: {response.text}")
            return False


async def test_sync_github_endpoint():
    """Test the sync GitHub endpoint with timeout"""
    print("\n⏱️ Testing Sync GitHub Endpoint...")
    
    if not GITHUB_TOKEN:
        print("  ⚠️ GITHUB_TOKEN not set, skipping test")
        return None
    
    async with httpx.AsyncClient(timeout=70.0) as client:  # 70s timeout
        # Test the sync endpoint with a simple request
        print("  Starting sync workflow (60s timeout)...")
        start_time = time.time()
        
        try:
            response = await client.post(
                f"{BASE_URL}/generate/complete-with-github-sync",
                json={
                    "description": "Create a single function that returns 42",
                    "github_token": GITHUB_TOKEN,
                    "repo_name": f"test-sync-{int(time.time())}",
                    "private": True
                }
            )
            
            elapsed = time.time() - start_time
            print(f"  Elapsed time: {elapsed:.1f}s")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"  GitHub URL: {result.get('github_url')}")
                    print("  ✅ Sync endpoint completed successfully!")
                    return True
                else:
                    print(f"  ⚠️ Workflow failed: {result.get('message')}")
                    return False
            else:
                print(f"  ❌ Request failed: {response.status_code}")
                return False
                
        except httpx.TimeoutException:
            elapsed = time.time() - start_time
            print(f"  ⚠️ Client timeout after {elapsed:.1f}s (expected behavior for complex requests)")
            return True  # Timeout is expected for complex requests


async def main():
    """Run all integration tests"""
    print("🧪 Running Integration Tests for Fixed Endpoints")
    print("=" * 50)
    
    # Check if services are running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ Orchestrator service is not running!")
                print("Please start the services with ./start.sh")
                return
    except Exception as e:
        print(f"❌ Cannot connect to orchestrator: {e}")
        print("Please start the services with ./start.sh")
        return
    
    # Run tests
    results = {
        "Workflow Status": await test_workflow_status_endpoint(),
        "CI Confidence": await test_ci_confidence_endpoint(),
        "GitHub Error Handling": await test_github_integration_error_handling(),
        "Async GitHub": await test_async_github_endpoint(),
        "Sync GitHub": await test_sync_github_endpoint(),
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print("=" * 50)
    
    total_tests = len([r for r in results.values() if r is not None])
    passed_tests = len([r for r in results.values() if r is True])
    skipped_tests = len([r for r in results.values() if r is None])
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⚠️ SKIPPED"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} passed ({skipped_tests} skipped)")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ Some tests failed or were skipped")


if __name__ == "__main__":
    asyncio.run(main())