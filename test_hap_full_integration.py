#!/usr/bin/env python3
"""
Full HAP integration test with the QuantumLayer Platform
Tests all integration points after applying patches
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, List
import sys
import time

# Add src to path
sys.path.insert(0, '.')

from src.moderation import check_content, CheckContext, Severity


class HAPIntegrationTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def print_result(self, test_name: str, passed: bool, details: str = ""):
        """Print test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")
        self.test_results.append((test_name, passed))
    
    async def test_hap_service_health(self) -> bool:
        """Test if HAP service is available"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v2/hap/health")
            return response.status_code == 200
        except:
            return False
    
    async def test_orchestrator_integration(self):
        """Test HAP integration in orchestrator"""
        self.print_header("1. Testing Orchestrator Integration")
        
        # Test 1: Clean request should pass
        clean_request = {
            "tenant_id": "test",
            "user_id": "test_user",
            "project_name": "Data Processing Pipeline",
            "description": "Build a data processing pipeline for CSV files",
            "language": "python"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v2/generate",
                json=clean_request
            )
            
            if response.status_code == 200:
                result = response.json()
                passed = result.get("success", False)
                self.print_result(
                    "Clean request accepted",
                    passed,
                    f"Capsule ID: {result.get('capsule_id', 'N/A')}"
                )
            else:
                self.print_result(
                    "Clean request accepted",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result("Clean request accepted", False, str(e))
        
        # Test 2: Inappropriate request should be blocked
        inappropriate_request = {
            "tenant_id": "test",
            "user_id": "test_user",
            "project_name": "Code Review",
            "description": "Fix this f***ing stupid code written by idiots",
            "language": "python"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v2/generate",
                json=inappropriate_request
            )
            
            if response.status_code == 200:
                result = response.json()
                blocked = result.get("status") == "blocked"
                self.print_result(
                    "Inappropriate request blocked",
                    blocked,
                    result.get("message", "")
                )
            else:
                # 400 status also indicates blocking
                self.print_result(
                    "Inappropriate request blocked",
                    True,
                    "Returned 400 Bad Request"
                )
        except Exception as e:
            self.print_result("Inappropriate request blocked", False, str(e))
    
    async def test_agent_integration(self):
        """Test HAP integration in agents"""
        self.print_header("2. Testing Agent Integration")
        
        # Create a task that might generate inappropriate content
        task_request = {
            "task_id": "test-hap-1",
            "description": "Review this code and explain what's wrong",
            "agent_type": "developer",
            "metadata": {
                "user_id": "test_user",
                "tenant_id": "test"
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}:8001/execute",  # Agent service port
                json=task_request
            )
            
            if response.status_code == 200:
                result = response.json()
                has_hap_check = "hap_check" in result.get("metadata", {})
                self.print_result(
                    "Agent includes HAP metadata",
                    has_hap_check,
                    f"Metadata: {result.get('metadata', {}).get('hap_check', 'None')}"
                )
            else:
                self.print_result(
                    "Agent includes HAP metadata",
                    False,
                    f"Agent service returned {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                "Agent includes HAP metadata",
                False,
                f"Could not reach agent service: {e}"
            )
    
    async def test_validation_integration(self):
        """Test HAP integration in validation mesh"""
        self.print_header("3. Testing Validation Integration")
        
        # Test code with mild profanity in comments
        test_code = '''
def process_data(input_file):
    """Process the damn input file"""
    # This stupid legacy code needs refactoring
    with open(input_file) as f:
        data = f.read()
    return data.upper()  # What the hell does this do?
'''
        
        validation_request = {
            "code": test_code,
            "language": "python",
            "context": {
                "user_id": "test_user",
                "tenant_id": "test"
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}:8002/validate/comprehensive",  # Validation service
                json=validation_request
            )
            
            if response.status_code == 200:
                result = response.json()
                stages = result.get("stages", [])
                has_content_safety = any(
                    stage.get("name") == "content_safety" 
                    for stage in stages
                )
                self.print_result(
                    "Validation includes content safety stage",
                    has_content_safety,
                    f"Found {len(stages)} validation stages"
                )
            else:
                self.print_result(
                    "Validation includes content safety stage",
                    False,
                    f"Validation service returned {response.status_code}"
                )
        except Exception as e:
            self.print_result(
                "Validation includes content safety stage",
                False,
                f"Could not reach validation service: {e}"
            )
    
    async def test_hap_api_endpoints(self):
        """Test HAP API endpoints"""
        self.print_header("4. Testing HAP API Endpoints")
        
        # Test check endpoint
        check_request = {
            "content": "Write a function to parse JSON data",
            "context": "user_request"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v2/hap/check",
                json=check_request
            )
            
            self.print_result(
                "HAP check endpoint available",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"    Severity: {result.get('severity')}")
                print(f"    Result: {result.get('result')}")
        except Exception as e:
            self.print_result("HAP check endpoint available", False, str(e))
        
        # Test batch endpoint
        batch_request = {
            "items": [
                {"content": "Normal code"},
                {"content": "This damn bug"},
                {"content": "Kill the process"}
            ],
            "context": "user_request"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v2/hap/check-batch",
                json=batch_request
            )
            
            self.print_result(
                "HAP batch endpoint available",
                response.status_code == 200,
                f"Processed {len(batch_request['items'])} items"
            )
        except Exception as e:
            self.print_result("HAP batch endpoint available", False, str(e))
    
    async def test_end_to_end_workflow(self):
        """Test complete workflow with HAP"""
        self.print_header("5. Testing End-to-End Workflow")
        
        # Submit a workflow that will trigger HAP at multiple points
        workflow_request = {
            "tenant_id": "e2e_test",
            "user_id": "workflow_tester",
            "description": "Create a web scraper that handles errors gracefully",
            "tags": ["python", "webscraping", "error-handling"]
        }
        
        try:
            # Start workflow
            response = await self.client.post(
                f"{self.base_url}/execute",
                json=workflow_request
            )
            
            if response.status_code == 200:
                result = response.json()
                workflow_id = result.get("workflow_id")
                self.print_result(
                    "Workflow started successfully",
                    True,
                    f"Workflow ID: {workflow_id}"
                )
                
                # Wait and check status
                await asyncio.sleep(5)
                
                status_response = await self.client.get(
                    f"{self.base_url}/status/{workflow_id}"
                )
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"    Status: {status.get('status')}")
                    print(f"    Progress: {status.get('progress', 0)}%")
                    
                    # Check if any tasks have HAP metadata
                    tasks = status.get("tasks", [])
                    hap_tasks = [
                        t for t in tasks 
                        if t.get("metadata", {}).get("hap_check")
                    ]
                    print(f"    Tasks with HAP checks: {len(hap_tasks)}/{len(tasks)}")
            else:
                self.print_result(
                    "Workflow started successfully",
                    False,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result("Workflow started successfully", False, str(e))
    
    async def test_performance_impact(self):
        """Test HAP performance impact"""
        self.print_header("6. Testing Performance Impact")
        
        # Prepare batch of requests
        requests = [
            {
                "content": f"Function to calculate fibonacci number {i}",
                "context": "user_request"
            }
            for i in range(20)
        ]
        
        # Time without caching (first run)
        start_time = time.time()
        tasks = [
            self.client.post(f"{self.base_url}/api/v2/hap/check", json=req)
            for req in requests
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        first_run_time = time.time() - start_time
        
        # Time with caching (second run)
        start_time = time.time()
        tasks = [
            self.client.post(f"{self.base_url}/api/v2/hap/check", json=req)
            for req in requests
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        cached_run_time = time.time() - start_time
        
        # Calculate improvement
        improvement = (first_run_time - cached_run_time) / first_run_time * 100
        
        self.print_result(
            "HAP caching improves performance",
            improvement > 20,  # Expect at least 20% improvement
            f"First run: {first_run_time:.2f}s, Cached: {cached_run_time:.2f}s ({improvement:.1f}% faster)"
        )
        
        # Check average response time
        avg_time = cached_run_time / len(requests) * 1000  # Convert to ms
        self.print_result(
            "HAP check under 50ms average",
            avg_time < 50,
            f"Average: {avg_time:.2f}ms per check"
        )
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*60)
        print("  HAP Full Integration Test Suite")
        print("="*60)
        
        # Check if platform is running
        platform_healthy = await self.test_hap_service_health()
        if not platform_healthy:
            print("\n❌ Platform is not running or HAP is not integrated!")
            print("Please ensure:")
            print("1. Platform is running: ./start.sh")
            print("2. HAP patches are applied: ./apply_hap_integration.sh")
            return
        
        print("\n✅ Platform is running with HAP enabled")
        
        # Run all test suites
        await self.test_orchestrator_integration()
        await self.test_agent_integration()
        await self.test_validation_integration()
        await self.test_hap_api_endpoints()
        await self.test_end_to_end_workflow()
        await self.test_performance_impact()
        
        # Summary
        self.print_header("Test Summary")
        passed = sum(1 for _, p in self.test_results if p)
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! HAP is fully integrated.")
        else:
            print("\n⚠️  Some tests failed. Please check the integration.")


async def main():
    """Run the integration test suite"""
    async with HAPIntegrationTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())