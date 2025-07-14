#!/usr/bin/env python3
"""
Test HAP integration with the running QuantumLayer Platform
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_hap_with_platform():
    """Test HAP with actual platform endpoints"""
    
    # Base URL for the platform
    base_url = "http://localhost:8000"
    
    print("🔍 Testing HAP Integration with QuantumLayer Platform\n")
    
    # Test cases with varying content
    test_cases = [
        {
            "name": "Clean Technical Request",
            "request": {
                "tenant_id": "demo",
                "user_id": "test_user",
                "description": "Create a Python function to calculate fibonacci numbers with memoization",
                "tags": ["python", "algorithms"]
            },
            "expected": "should_pass"
        },
        {
            "name": "Mild Profanity",
            "request": {
                "tenant_id": "demo", 
                "user_id": "frustrated_dev",
                "description": "Fix this damn bug in the authentication system",
                "tags": ["bugfix", "auth"]
            },
            "expected": "should_flag"
        },
        {
            "name": "Inappropriate Content",
            "request": {
                "tenant_id": "demo",
                "user_id": "angry_user", 
                "description": "This stupid code is crap! The idiot who wrote it should be fired!",
                "tags": ["review"]
            },
            "expected": "should_block"
        },
        {
            "name": "Technical Terms Test",
            "request": {
                "tenant_id": "demo",
                "user_id": "dev_user",
                "description": "Implement a process killer that terminates zombie processes using force flag",
                "tags": ["system", "processes"]
            },
            "expected": "should_pass"
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, check if HAP endpoints are available
        print("1️⃣  Checking HAP service health...\n")
        try:
            response = await client.get(f"{base_url}/api/v2/hap/health")
            if response.status_code == 200:
                print("✅ HAP service is healthy\n")
            else:
                print("❌ HAP service not responding properly")
                return
        except Exception as e:
            print(f"❌ Cannot connect to HAP service: {e}")
            print("Make sure the platform is running with HAP enabled")
            return
        
        # Test each case
        print("2️⃣  Testing content moderation...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"Test {i}: {test_case['name']}")
            print(f"Content: \"{test_case['request']['description']}\"")
            
            # Test direct HAP check endpoint
            try:
                hap_response = await client.post(
                    f"{base_url}/api/v2/hap/check",
                    json={
                        "content": test_case['request']['description'],
                        "context": "user_request"
                    }
                )
                
                if hap_response.status_code == 200:
                    hap_result = hap_response.json()
                    print(f"HAP Result: {hap_result['severity']} - {hap_result['result']}")
                    
                    if hap_result.get('categories'):
                        print(f"Categories: {', '.join(hap_result['categories'])}")
                    if hap_result.get('explanation'):
                        print(f"Explanation: {hap_result['explanation']}")
                else:
                    print(f"HAP check failed: {hap_response.status_code}")
                    
            except Exception as e:
                print(f"Error checking content: {e}")
            
            # Test with actual execution endpoint
            try:
                exec_response = await client.post(
                    f"{base_url}/execute",
                    json=test_case['request']
                )
                
                if exec_response.status_code == 200:
                    print("✅ Request accepted by platform")
                elif exec_response.status_code == 400:
                    error_detail = exec_response.json()
                    print(f"🚫 Request blocked: {error_detail.get('detail', 'Unknown reason')}")
                else:
                    print(f"❓ Unexpected response: {exec_response.status_code}")
                    
            except Exception as e:
                print(f"Error executing request: {e}")
            
            print("-" * 60)
            print()
        
        # Test batch checking
        print("3️⃣  Testing batch content checking...\n")
        
        batch_items = [
            {"content": "Write clean code", "metadata": {"id": "1"}},
            {"content": "This damn bug", "metadata": {"id": "2"}},
            {"content": "Kill the process", "metadata": {"id": "3"}},
            {"content": "What the hell", "metadata": {"id": "4"}}
        ]
        
        try:
            batch_response = await client.post(
                f"{base_url}/api/v2/hap/check-batch",
                json={
                    "items": batch_items,
                    "context": "user_request"
                }
            )
            
            if batch_response.status_code == 200:
                results = batch_response.json()
                print(f"Batch processed {len(results)} items:")
                for item, result in zip(batch_items, results):
                    print(f"  '{item['content']}' → {result['severity']}")
            else:
                print(f"Batch check failed: {batch_response.status_code}")
                
        except Exception as e:
            print(f"Error in batch check: {e}")
        
        print("\n" + "-" * 60)
        
        # Test configuration endpoint
        print("\n4️⃣  Testing HAP configuration...\n")
        
        try:
            config_response = await client.get(f"{base_url}/api/v2/hap/config")
            if config_response.status_code == 200:
                config = config_response.json()
                print("Current HAP Configuration:")
                print(f"  Sensitivity: {config.get('sensitivity', 'default')}")
                print(f"  Categories enabled: {json.dumps(config.get('categories', {}), indent=4)}")
            else:
                print(f"Failed to get config: {config_response.status_code}")
                
        except Exception as e:
            print(f"Error getting config: {e}")


async def test_with_real_workflow():
    """Test HAP in a complete workflow"""
    
    print("\n\n🚀 Testing Complete Workflow with HAP\n")
    
    # Create a workflow that should trigger HAP at different stages
    workflow_request = {
        "tenant_id": "demo",
        "user_id": "workflow_test_user",
        "project_name": "Code Review System",
        "description": """
        Build a code review system that can analyze this crappy legacy code.
        The previous developers were idiots who didn't follow any standards.
        I need this damn thing working ASAP!
        """,
        "requirements": [
            "Analyze code quality",
            "Identify performance issues",
            "Generate improvement suggestions"
        ],
        "tech_stack": ["Python", "FastAPI"]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Submitting workflow with inappropriate language...")
        print(f"Description preview: {workflow_request['description'][:100]}...")
        
        try:
            # Try to create a capsule
            response = await client.post(
                "http://localhost:8000/generate/capsule",
                json=workflow_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Workflow accepted (ID: {result.get('request_id')})")
                print("Note: Content may have been filtered internally")
                
                # Check the workflow status
                await asyncio.sleep(2)
                status_response = await client.get(
                    f"http://localhost:8000/status/{result['request_id']}"
                )
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"Workflow status: {status.get('status')}")
                    
            elif response.status_code == 400:
                error = response.json()
                print(f"\n🚫 Workflow blocked by HAP: {error.get('detail')}")
                
                # Show cleaned version
                print("\n✨ Here's a cleaned version that would pass:")
                cleaned_desc = """
                Build a code review system that can analyze legacy code.
                The existing codebase has quality issues and lacks standards.
                This is an urgent priority project.
                """
                print(cleaned_desc)
                
            else:
                print(f"\n❓ Unexpected response: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def show_hap_statistics():
    """Display HAP statistics if available"""
    
    print("\n\n📊 HAP System Statistics\n")
    
    async with httpx.AsyncClient() as client:
        try:
            # Get violation stats
            response = await client.get(
                "http://localhost:8000/api/v2/hap/stats?period=day"
            )
            
            if response.status_code == 200:
                stats = response.json()
                print("Today's Statistics:")
                print(f"  Total checks: {stats.get('total_checks', 0)}")
                print(f"  Violations: {stats.get('total_violations', 0)}")
                print(f"  Violation rate: {stats.get('violation_rate', 0):.1%}")
                
                if stats.get('by_severity'):
                    print("\nBy Severity:")
                    for sev, count in stats['by_severity'].items():
                        print(f"    {sev}: {count}")
                
                if stats.get('by_category'):
                    print("\nBy Category:")
                    for cat, count in stats['by_category'].items():
                        print(f"    {cat}: {count}")
                        
            else:
                print("Statistics not available (may require auth)")
                
        except Exception as e:
            print(f"Could not retrieve statistics: {e}")


async def main():
    """Run all integration tests"""
    
    print("=" * 70)
    print("   HAP Platform Integration Test")
    print("=" * 70)
    
    # Check if platform is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                print("❌ Platform is not running! Start it with ./start.sh")
                return
    except:
        print("❌ Cannot connect to platform at http://localhost:8000")
        print("Please start the platform first with: ./start.sh")
        return
    
    # Run tests
    await test_hap_with_platform()
    await test_with_real_workflow()
    await show_hap_statistics()
    
    print("\n✅ Integration tests completed!")
    print("\nTo see more HAP features:")
    print("- Run the interactive demo: python demo_hap_system.py")
    print("- Check API docs: http://localhost:8000/docs#/HAP")
    print("- View logs: tail -f logs/orchestrator.log | grep HAP")


if __name__ == "__main__":
    asyncio.run(main())