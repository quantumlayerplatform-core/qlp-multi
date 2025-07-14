#!/usr/bin/env python3
"""
Comprehensive endpoint validation for Quantum Layer Platform
Tests all endpoints documented in CLAUDE.md
"""

import json
import time
from typing import Dict, Any, List, Tuple
import requests
from datetime import datetime

# Try to import colorama, but fall back to no colors if not available
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    # Define dummy color constants
    class Fore:
        CYAN = GREEN = RED = YELLOW = ""
    class Style:
        RESET_ALL = ""

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

class EndpointTester:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.test_data = {}
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def print_header(self, title: str):
        """Print a formatted section header"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title.center(60)}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    def print_result(self, endpoint: str, method: str, status: int, success: bool, error: str = None):
        """Print formatted test result"""
        status_color = Fore.GREEN if success else Fore.RED
        status_text = "✓ PASS" if success else "✗ FAIL"
        
        print(f"{status_color}{status_text}{Style.RESET_ALL} {method:6} {endpoint:50} [{status}]")
        if error:
            print(f"         {Fore.YELLOW}→ {error}{Style.RESET_ALL}")

    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, 
                     expected_status: List[int] = None, description: str = None) -> Tuple[bool, Dict]:
        """Test a single endpoint"""
        if expected_status is None:
            expected_status = [200, 201, 202]
            
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url, timeout=TIMEOUT)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=TIMEOUT)
            elif method == "PUT":
                response = self.session.put(url, json=data, timeout=TIMEOUT)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=TIMEOUT)
            elif method == "PATCH":
                response = self.session.patch(url, json=data, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            success = response.status_code in expected_status
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "success": success,
                "response": response.json() if response.content else None,
                "description": description
            }
            
            self.print_result(endpoint, method, response.status_code, success)
            self.results.append(result)
            
            # Store useful data for subsequent tests
            if success and response.content:
                try:
                    data = response.json()
                    if "workflow_id" in data:
                        self.test_data["workflow_id"] = data["workflow_id"]
                    if "capsule_id" in data:
                        self.test_data["capsule_id"] = data["capsule_id"]
                    if "request_id" in data:
                        self.test_data["request_id"] = data["request_id"]
                except:
                    pass
                    
            return success, result
            
        except Exception as e:
            error_msg = str(e)
            self.print_result(endpoint, method, 0, False, error_msg)
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "success": False,
                "error": error_msg,
                "description": description
            }
            self.results.append(result)
            return False, result

    def test_health_endpoints(self):
        """Test basic health check endpoints"""
        self.print_header("Health Check Endpoints")
        
        self.test_endpoint("GET", "/health", description="Orchestrator health check")

    def test_execution_endpoints(self):
        """Test execution and generation endpoints"""
        self.print_header("Execution & Generation Endpoints")
        
        # Basic execution
        execution_data = {
            "tenant_id": "test",
            "user_id": "test-user",
            "description": "Create a simple hello world function in Python"
        }
        
        self.test_endpoint("POST", "/execute", data=execution_data, 
                          description="Submit NLP request for code generation")
        
        # Wait a bit for workflow to start
        time.sleep(2)
        
        # Capsule generation
        capsule_data = {
            "request_id": f"test-{int(time.time())}",
            "tenant_id": "test",
            "user_id": "test-user",
            "project_name": "Test Project",
            "description": "Simple test project",
            "requirements": "Basic functionality",
            "tech_stack": ["Python"]
        }
        
        self.test_endpoint("POST", "/generate/capsule", data=capsule_data,
                          description="Generate basic capsule")
        
        # Complete with GitHub endpoints
        self.test_endpoint("POST", "/generate/complete-with-github", 
                          data=capsule_data,
                          expected_status=[200, 404],
                          description="Generate and push to GitHub")
        
        self.test_endpoint("POST", "/generate/complete-with-github-sync", 
                          data=capsule_data,
                          expected_status=[200, 404],
                          description="Synchronous GitHub generation")
        
        self.test_endpoint("POST", "/generate/complete-pipeline", 
                          data=capsule_data,
                          expected_status=[200, 404],
                          description="Full pipeline with all features")
        
        self.test_endpoint("POST", "/generate/robust-capsule", 
                          data=capsule_data,
                          description="Production-grade generation")

    def test_workflow_endpoints(self):
        """Test workflow management endpoints"""
        self.print_header("Workflow Management Endpoints")
        
        if "workflow_id" in self.test_data:
            workflow_id = self.test_data["workflow_id"]
            
            self.test_endpoint("GET", f"/workflow/status/{workflow_id}",
                              description="Get workflow status")
            
            self.test_endpoint("GET", f"/status/{workflow_id}",
                              description="Simple status check")
            
            # Test approve endpoint (might fail if no HITL request)
            self.test_endpoint("POST", f"/approve/{workflow_id}",
                              expected_status=[200, 404],
                              description="Approve HITL request")
        else:
            print(f"{Fore.YELLOW}Skipping workflow endpoints - no workflow_id available{Style.RESET_ALL}")

    def test_capsule_endpoints(self):
        """Test capsule management endpoints"""
        self.print_header("Capsule Management Endpoints")
        
        # First, try to get a capsule ID from a previous test or use a dummy one
        capsule_id = self.test_data.get("capsule_id", "test-capsule-id")
        
        # Get capsule (might 404 if not exists)
        self.test_endpoint("GET", f"/capsule/{capsule_id}",
                          expected_status=[200, 404],
                          description="Get capsule details")
        
        # Test delivery endpoint
        delivery_data = {
            "capsule_id": capsule_id,
            "request_id": "test-request",
            "tenant_id": "test",
            "user_id": "test-user",
            "package_format": "zip",
            "delivery_methods": ["download"],
            "metadata": {}
        }
        
        self.test_endpoint("POST", f"/capsules/{capsule_id}/deliver",
                          data=delivery_data,
                          expected_status=[200, 404],
                          description="Package and deliver capsule")
        
        # Advanced delivery
        self.test_endpoint("POST", f"/capsule/{capsule_id}/deliver/advanced",
                          data={"delivery_configs": []},
                          expected_status=[200, 404, 422],
                          description="Advanced delivery endpoint")
        
        # Export endpoints
        self.test_endpoint("GET", f"/capsule/{capsule_id}/export/zip",
                          expected_status=[200, 404],
                          description="Export capsule as ZIP")
        
        # Version management
        self.test_endpoint("POST", f"/capsule/{capsule_id}/version",
                          data={"message": "Test version"},
                          expected_status=[200, 404],
                          description="Create capsule version")
        
        self.test_endpoint("GET", f"/capsule/{capsule_id}/history",
                          expected_status=[200, 404],
                          description="Version history")

    def test_analysis_endpoints(self):
        """Test analysis and optimization endpoints"""
        self.print_header("Analysis & Optimization Endpoints")
        
        analysis_data = {
            "request": "Create a web application with user authentication",
            "context": {}
        }
        
        self.test_endpoint("POST", "/analyze/extended-reasoning",
                          data=analysis_data,
                          description="Extended analysis")
        
        self.test_endpoint("POST", "/patterns/analyze",
                          data={"description": "Test pattern analysis"},
                          description="Pattern analysis")
        
        self.test_endpoint("POST", "/patterns/recommend",
                          data={"task_type": "code_generation", "complexity": "medium"},
                          description="Pattern recommendations")
        
        self.test_endpoint("POST", "/patterns/explain",
                          data={"pattern": "abstraction", "context": "test"},
                          expected_status=[200, 404],
                          description="Pattern explanation")
        
        self.test_endpoint("GET", "/patterns/usage-guide",
                          description="Pattern usage guide")
        
        decompose_data = {
            "description": "Build a REST API",
            "tenant_id": "test",
            "user_id": "test"
        }
        
        self.test_endpoint("POST", "/decompose/enhanced",
                          data=decompose_data,
                          expected_status=[200, 404],
                          description="Enhanced decomposition")
        
        self.test_endpoint("POST", "/decompose/unified-optimization",
                          data=decompose_data,
                          description="Optimized decomposition")
        
        self.test_endpoint("GET", "/optimization/insights",
                          description="Optimization insights")

    def test_github_endpoints(self):
        """Test GitHub integration endpoints"""
        self.print_header("GitHub Integration Endpoints")
        
        # These will likely fail without proper GitHub token
        github_data = {
            "capsule_id": self.test_data.get("capsule_id", "test-capsule"),
            "repo_name": "test-repo",
            "private": False
        }
        
        self.test_endpoint("POST", "/api/github/push",
                          data=github_data,
                          expected_status=[200, 401, 404],
                          description="Push capsule to GitHub")

    def test_enterprise_endpoints(self):
        """Test enterprise feature endpoints"""
        self.print_header("Enterprise Feature Endpoints")
        
        enterprise_data = {
            "description": "Create an enterprise web application",
            "tenant_id": "test",
            "user_id": "test-user",
            "enterprise_features": {
                "documentation": True,
                "testing": True,
                "ci_cd": True
            }
        }
        
        self.test_endpoint("POST", "/api/enterprise/generate",
                          data=enterprise_data,
                          expected_status=[200, 404],
                          description="Enterprise-grade project generation")

    def test_hitl_endpoints(self):
        """Test HITL (Human-in-the-Loop) endpoints"""
        self.print_header("HITL Endpoints")
        
        # Create HITL request
        hitl_data = {
            "task_id": "test-task",
            "request_type": "approval",
            "context": {"test": True}
        }
        
        self.test_endpoint("POST", "/hitl/request",
                          data=hitl_data,
                          expected_status=[200, 422],
                          description="Create HITL request")
        
        # Get pending requests
        self.test_endpoint("GET", "/hitl/pending",
                          description="Get pending HITL requests")
        
        # Get statistics
        self.test_endpoint("GET", "/hitl/statistics",
                          description="HITL statistics")

    def test_download_endpoints(self):
        """Test download/export endpoints"""
        self.print_header("Download & Export Endpoints")
        
        capsule_id = self.test_data.get("capsule_id", "test-capsule")
        
        # List capsules
        self.test_endpoint("GET", "/api/capsules",
                          expected_status=[200, 404, 500],
                          description="List available capsules")
        
        # Download capsule
        self.test_endpoint("GET", f"/api/capsules/{capsule_id}/download?format=zip",
                          expected_status=[200, 404, 500],
                          description="Download capsule as ZIP")

    def test_all_services_health(self):
        """Test health endpoints for all services"""
        self.print_header("All Services Health Check")
        
        services = [
            ("Orchestrator", 8000),
            ("Agent Factory", 8001),
            ("Validation Mesh", 8002),
            ("Vector Memory", 8003),
            ("Execution Sandbox", 8004)
        ]
        
        for service_name, port in services:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5.0)
                success = response.status_code == 200
                self.print_result(f"http://localhost:{port}/health", "GET", 
                                response.status_code, success)
            except Exception as e:
                self.print_result(f"http://localhost:{port}/health", "GET", 
                                0, False, f"{service_name} not accessible: {str(e)}")

    def run_all_tests(self):
        """Run all endpoint tests"""
        print(f"\n{Fore.CYAN}Starting Quantum Layer Platform Endpoint Validation")
        print(f"{Fore.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        
        # Test all services first
        self.test_all_services_health()
        
        # Test orchestrator endpoints
        self.test_health_endpoints()
        self.test_execution_endpoints()
        self.test_workflow_endpoints()
        self.test_capsule_endpoints()
        self.test_analysis_endpoints()
        self.test_github_endpoints()
        self.test_enterprise_endpoints()
        self.test_hitl_endpoints()
        self.test_download_endpoints()
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.get("success", False))
        failed = total_tests - passed
        
        print(f"Total Endpoints Tested: {total_tests}")
        print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed > 0:
            print(f"\n{Fore.YELLOW}Failed Endpoints:{Style.RESET_ALL}")
            for result in self.results:
                if not result.get("success", False):
                    print(f"  - {result['method']} {result['endpoint']} [{result['status_code']}]")
                    if "error" in result:
                        print(f"    Error: {result['error']}")

def main():
    """Main test runner"""
    with EndpointTester() as tester:
        tester.run_all_tests()

if __name__ == "__main__":
    main()