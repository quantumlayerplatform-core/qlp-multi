#!/usr/bin/env python3
"""
Quantum Layer Platform - Full End-to-End Integration Test
Tests the complete system with all services running
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
import requests

sys.path.append('.')

# Set database URL for the test
os.environ['DATABASE_URL'] = 'postgresql://qlp_user:qlp_password@127.0.0.1:15432/qlp_db'

from src.common.models import ExecutionRequest
from src.orchestrator.main import app as orchestrator_app
from src.agents.main import app as agent_app
from src.validation.main import app as validation_app
from src.memory.main import app as memory_app
from src.sandbox.main import app as sandbox_app


class FullE2ETest:
    """Complete end-to-end test with all services"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = {}
        self.services_healthy = False
    
    def log(self, message: str, status: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbol = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "RUNNING": "🔄"
        }.get(status, "•")
        print(f"[{timestamp}] {symbol} {message}")
    
    def check_service_health(self, name: str, port: int) -> bool:
        """Check if a service is healthy"""
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                self.log(f"{name} is healthy on port {port}", "SUCCESS")
                return True
            else:
                self.log(f"{name} returned status {response.status_code}", "WARNING")
                return False
        except Exception as e:
            self.log(f"{name} not responding: {str(e)}", "ERROR")
            return False
    
    def test_infrastructure(self):
        """Test 1: Verify infrastructure services"""
        self.log("Testing infrastructure services...", "RUNNING")
        
        # Check PostgreSQL via psql
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "exec", "qlp-postgres", "psql", "-U", "qlp_user", "-d", "qlp_db", "-c", "SELECT 1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log("PostgreSQL is healthy", "SUCCESS")
                self.test_results["PostgreSQL"] = True
            else:
                self.log("PostgreSQL check failed", "ERROR")
                self.test_results["PostgreSQL"] = False
        except Exception as e:
            self.log(f"PostgreSQL error: {e}", "ERROR")
            self.test_results["PostgreSQL"] = False
        
        # Check Redis
        try:
            result = subprocess.run(
                ["docker", "exec", "qlp-redis", "redis-cli", "ping"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "PONG" in result.stdout:
                self.log("Redis is healthy", "SUCCESS")
                self.test_results["Redis"] = True
            else:
                self.log("Redis check failed", "ERROR")
                self.test_results["Redis"] = False
        except Exception as e:
            self.log(f"Redis error: {e}", "ERROR")
            self.test_results["Redis"] = False
        
        # Check Qdrant
        try:
            response = requests.get("http://localhost:6333/", timeout=5)
            if response.status_code == 200:
                self.log("Qdrant is healthy", "SUCCESS")
                self.test_results["Qdrant"] = True
            else:
                self.log("Qdrant check failed", "ERROR")
                self.test_results["Qdrant"] = False
        except Exception as e:
            self.log(f"Qdrant error: {e}", "ERROR")
            self.test_results["Qdrant"] = False
    
    def test_services(self):
        """Test 2: Check if QLP services are running"""
        self.log("Checking QLP services...", "RUNNING")
        
        services = [
            ("Orchestrator", 8000),
            ("Agent Factory", 8001),
            ("Validation Mesh", 8002),
            ("Vector Memory", 8003),
            ("Execution Sandbox", 8004)
        ]
        
        all_healthy = True
        for name, port in services:
            if self.check_service_health(name, port):
                self.test_results[name] = True
            else:
                self.test_results[name] = False
                all_healthy = False
        
        self.services_healthy = all_healthy
        
        if not all_healthy:
            self.log("Some services are not running. Starting them now...", "WARNING")
            # In a real scenario, we would start the services here
            self.log("Please run ./start.sh in another terminal to start services", "WARNING")
    
    async def test_code_generation(self):
        """Test 3: Test actual code generation through the API"""
        self.log("Testing code generation API...", "RUNNING")
        
        # Create a test request
        request_data = {
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "description": "Create a Python function that calculates the fibonacci sequence",
            "requirements": "The function should be efficient and handle large numbers",
            "metadata": {
                "language": "python",
                "complexity": "medium"
            }
        }
        
        try:
            # Make API request to orchestrator using the generate endpoint
            self.log("Sending code generation request...", "INFO")
            response = requests.post(
                f"{self.base_url}/generate/capsule",
                json=request_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log("Code generation successful!", "SUCCESS")
                self.log(f"Request ID: {result.get('request_id', 'N/A')}", "INFO")
                
                # Check if capsule was created
                if 'capsule_id' in result:
                    self.log(f"Capsule created: {result['capsule_id']}", "SUCCESS")
                    self.test_results["Code Generation"] = True
                    
                    # Try to retrieve the capsule
                    capsule_response = requests.get(
                        f"{self.base_url}/capsule/{result['capsule_id']}",
                        timeout=10
                    )
                    
                    if capsule_response.status_code == 200:
                        capsule = capsule_response.json()
                        self.log("Capsule retrieved successfully", "SUCCESS")
                        
                        # Display generated code
                        if 'source_code' in capsule:
                            self.log("Generated code files:", "INFO")
                            for filename in capsule['source_code'].keys():
                                self.log(f"  - {filename}", "INFO")
                else:
                    self.log("No capsule ID in response", "WARNING")
                    self.test_results["Code Generation"] = False
            else:
                self.log(f"Code generation failed: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                self.test_results["Code Generation"] = False
                
        except requests.exceptions.ConnectionError:
            self.log("Cannot connect to orchestrator. Are services running?", "ERROR")
            self.test_results["Code Generation"] = False
        except Exception as e:
            self.log(f"Code generation error: {str(e)}", "ERROR")
            self.test_results["Code Generation"] = False
    
    async def test_validation(self):
        """Test 4: Test code validation"""
        self.log("Testing code validation...", "RUNNING")
        
        # Sample code to validate
        test_code = '''
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''
        
        validation_request = {
            "code": test_code,
            "language": "python",
            "context": {
                "purpose": "fibonacci calculation",
                "requirements": ["efficiency", "correctness"]
            }
        }
        
        try:
            response = requests.post(
                "http://localhost:8002/validate",
                json=validation_request,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log("Validation completed", "SUCCESS")
                self.log(f"Validation status: {result.get('status', 'unknown')}", "INFO")
                self.test_results["Validation"] = True
            else:
                self.log(f"Validation failed: {response.status_code}", "ERROR")
                self.test_results["Validation"] = False
                
        except requests.exceptions.ConnectionError:
            self.log("Cannot connect to validation service", "ERROR")
            self.test_results["Validation"] = False
        except Exception as e:
            self.log(f"Validation error: {str(e)}", "ERROR")
            self.test_results["Validation"] = False
    
    async def test_memory_storage(self):
        """Test 5: Test vector memory storage"""
        self.log("Testing vector memory...", "RUNNING")
        
        # Test data
        test_embedding = {
            "id": "test-doc-1",
            "content": "Python fibonacci function implementation",
            "embedding": [0.1] * 384,  # Mock embedding
            "metadata": {
                "type": "code",
                "language": "python",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            # Store in vector memory
            response = requests.post(
                "http://localhost:8003/store/code",
                json=test_embedding,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("Vector stored successfully", "SUCCESS")
                
                # Search for similar vectors
                search_request = {
                    "query": "fibonacci implementation",
                    "limit": 5
                }
                
                search_response = requests.post(
                    "http://localhost:8003/search/code",
                    json=search_request,
                    timeout=10
                )
                
                if search_response.status_code == 200:
                    results = search_response.json()
                    self.log(f"Found {len(results.get('results', []))} similar items", "SUCCESS")
                    self.test_results["Vector Memory"] = True
                else:
                    self.log("Vector search failed", "ERROR")
                    self.test_results["Vector Memory"] = False
            else:
                self.log(f"Vector storage failed: {response.status_code}", "ERROR")
                self.test_results["Vector Memory"] = False
                
        except requests.exceptions.ConnectionError:
            self.log("Cannot connect to memory service", "ERROR")
            self.test_results["Vector Memory"] = False
        except Exception as e:
            self.log(f"Memory error: {str(e)}", "ERROR")
            self.test_results["Vector Memory"] = False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("🔥 QUANTUM LAYER PLATFORM - FULL E2E TEST RESULTS")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for v in self.test_results.values() if v)
        
        print(f"\n📊 Test Results:")
        for test, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} - {test}")
        
        print(f"\n📈 Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {total_tests - passed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! SYSTEM IS FULLY OPERATIONAL! 🎉")
        else:
            print("\n⚠️  Some tests failed. Please check the logs above.")
        
        print("="*60)


async def main():
    """Run the full end-to-end test"""
    print("🌟 QUANTUM LAYER PLATFORM - FULL END-TO-END TEST")
    print("Testing complete system with all components")
    print("-" * 60)
    
    test = FullE2ETest()
    
    # Test 1: Infrastructure
    test.test_infrastructure()
    
    # Test 2: Services
    test.test_services()
    
    if test.services_healthy:
        # Test 3: Code Generation
        await test.test_code_generation()
        
        # Test 4: Validation
        await test.test_validation()
        
        # Test 5: Memory
        await test.test_memory_storage()
    else:
        test.log("Skipping API tests as services are not running", "WARNING")
        test.log("Please start services with ./start.sh and run again", "INFO")
    
    # Print summary
    test.print_summary()


if __name__ == "__main__":
    asyncio.run(main())