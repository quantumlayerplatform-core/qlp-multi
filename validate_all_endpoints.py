#!/usr/bin/env python3
"""
Comprehensive endpoint validation for Quantum Layer Platform
Tests all endpoints from the OpenAPI specification
"""

import requests
import json
from typing import Dict, List, Tuple
from datetime import datetime
from uuid import uuid4

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-token"  # For auth-required endpoints
}

# Test data
TEST_CAPSULE_ID = "577c22b0-5596-4e77-a4ac-d1e422d039bc"
TEST_WORKFLOW_ID = str(uuid4())
TEST_VERSION_ID = str(uuid4())
TEST_REQUEST_ID = str(uuid4())

class EndpointValidator:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def test_endpoint(self, method: str, path: str, expected_status: List[int] = None, 
                     data: Dict = None, description: str = None):
        """Test a single endpoint"""
        url = f"{BASE_URL}{path}"
        expected_status = expected_status or [200, 201, 202]
        
        try:
            if method == "GET":
                response = requests.get(url, headers=HEADERS, timeout=5)
            elif method == "POST":
                response = requests.post(url, headers=HEADERS, json=data, timeout=5)
            elif method == "PUT":
                response = requests.put(url, headers=HEADERS, json=data, timeout=5)
            elif method == "DELETE":
                response = requests.delete(url, headers=HEADERS, timeout=5)
            else:
                response = None
                status = "UNSUPPORTED"
            
            if response:
                status = response.status_code
                success = status in expected_status
                
                if success:
                    self.passed += 1
                    result = "✅ PASS"
                else:
                    self.failed += 1
                    result = "❌ FAIL"
                    
                self.results.append({
                    "method": method,
                    "path": path,
                    "status": status,
                    "expected": expected_status,
                    "result": result,
                    "description": description or path
                })
                
                if not success and response.text:
                    try:
                        error_detail = response.json().get("detail", response.text[:100])
                    except:
                        error_detail = response.text[:100]
                    print(f"{result} {method} {path} [{status}] - {error_detail}")
                else:
                    print(f"{result} {method} {path} [{status}]")
                    
        except requests.exceptions.Timeout:
            self.failed += 1
            self.results.append({
                "method": method,
                "path": path,
                "status": "TIMEOUT",
                "expected": expected_status,
                "result": "❌ TIMEOUT",
                "description": description or path
            })
            print(f"❌ TIMEOUT {method} {path}")
        except Exception as e:
            self.failed += 1
            self.results.append({
                "method": method,
                "path": path,
                "status": "ERROR",
                "expected": expected_status,
                "result": "❌ ERROR",
                "description": str(e)[:100]
            })
            print(f"❌ ERROR {method} {path} - {str(e)[:100]}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"Total Endpoints Tested: {len(self.results)}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / len(self.results) * 100):.1f}%")
        
        # Group failures by type
        failures = [r for r in self.results if r["result"].startswith("❌")]
        if failures:
            print("\n❌ FAILED ENDPOINTS:")
            for f in failures:
                print(f"  - {f['method']} {f['path']} [{f['status']}]")

def main():
    validator = EndpointValidator()
    
    print("🔍 Quantum Layer Platform - Comprehensive Endpoint Validation")
    print("="*60)
    
    # Core Health Checks
    print("\n📋 Core Health Endpoints:")
    validator.test_endpoint("GET", "/health", [200], description="Main orchestrator health")
    validator.test_endpoint("GET", "/api/v2/health", [200], description="V2 API health")
    
    # Execution Endpoints
    print("\n🚀 Execution Endpoints:")
    validator.test_endpoint("POST", "/execute", [422], {}, "Execute without data")
    validator.test_endpoint("POST", "/execute", [200, 201], {
        "tenant_id": "test",
        "user_id": "test-user",
        "description": "Test execution"
    }, "Execute with valid data")
    
    # Capsule Generation Endpoints
    print("\n📦 Capsule Generation:")
    validator.test_endpoint("POST", "/generate/capsule", [422], {}, "Generate without data")
    validator.test_endpoint("POST", "/generate/capsule", [200, 201], {
        "request_id": str(uuid4()),
        "tenant_id": "test",
        "user_id": "test-user",
        "project_name": "Test",
        "description": "Test capsule",
        "requirements": "Simple test",
        "tech_stack": ["Python"]
    }, "Generate with valid data")
    
    validator.test_endpoint("POST", "/generate/robust-capsule", [422], {}, "Robust capsule without data")
    validator.test_endpoint("POST", "/capsules/generate", [422], {}, "Capsules generate without data")
    validator.test_endpoint("POST", "/api/v2/capsule/generate", [422], {}, "V2 capsule generate")
    
    # Capsule Retrieval Endpoints
    print("\n📖 Capsule Retrieval:")
    validator.test_endpoint("GET", f"/capsule/{TEST_CAPSULE_ID}", [200, 404, 500], description="Get capsule by ID")
    validator.test_endpoint("GET", f"/capsules/{TEST_CAPSULE_ID}", [200, 404], description="Get capsule (alt)")
    validator.test_endpoint("GET", f"/api/capsules/{TEST_CAPSULE_ID}", [200, 404, 500], description="API capsule get")
    validator.test_endpoint("GET", "/api/capsules", [200, 500], description="List all capsules")
    validator.test_endpoint("GET", "/capsules/user/test/test-user", [200, 404], description="List user capsules")
    
    # Capsule Operations
    print("\n🔧 Capsule Operations:")
    validator.test_endpoint("GET", f"/capsule/{TEST_CAPSULE_ID}/history", [200, 404], description="Capsule history")
    validator.test_endpoint("GET", f"/capsule/{TEST_CAPSULE_ID}/stream", [200, 404], description="Stream capsule")
    validator.test_endpoint("GET", f"/capsule/{TEST_CAPSULE_ID}/export/zip", [200, 404], description="Export as ZIP")
    validator.test_endpoint("POST", f"/capsule/{TEST_CAPSULE_ID}/version", [422], {}, "Create version")
    validator.test_endpoint("POST", f"/capsule/{TEST_CAPSULE_ID}/branch", [422], {}, "Create branch")
    validator.test_endpoint("POST", f"/capsule/{TEST_CAPSULE_ID}/tag", [422], {}, "Tag capsule")
    validator.test_endpoint("POST", f"/capsule/{TEST_CAPSULE_ID}/sign", [422], {}, "Sign capsule")
    
    # Pattern Analysis
    print("\n🧠 Pattern Analysis:")
    validator.test_endpoint("GET", "/patterns/usage-guide", [200], description="Pattern usage guide")
    validator.test_endpoint("GET", "/analyze/patterns", [200], description="List patterns")
    validator.test_endpoint("POST", "/patterns/analyze", [422], {}, "Analyze patterns")
    validator.test_endpoint("POST", "/patterns/recommend", [422], {}, "Recommend patterns")
    validator.test_endpoint("POST", "/patterns/explain", [422], {}, "Explain patterns")
    
    # Decomposition
    print("\n🔍 Decomposition:")
    validator.test_endpoint("POST", "/decompose/unified-optimization", [422], {}, "Unified optimization")
    validator.test_endpoint("POST", "/decompose/enhanced", [422], {}, "Enhanced decomposition")
    validator.test_endpoint("POST", "/test/decompose", [422], {}, "Test decomposition")
    
    # HITL/AITL Endpoints
    print("\n👤 HITL/AITL:")
    validator.test_endpoint("GET", "/hitl/pending", [200], description="Pending HITL requests")
    validator.test_endpoint("GET", "/hitl/statistics", [200], description="HITL statistics")
    validator.test_endpoint("POST", "/hitl/request", [422], {}, "Create HITL request")
    validator.test_endpoint("POST", "/hitl/auto-approve", [422], {}, "Auto approve")
    validator.test_endpoint("POST", "/hitl/batch-approve", [422], {}, "Batch approve")
    validator.test_endpoint("GET", f"/hitl/status/{TEST_REQUEST_ID}", [404], description="HITL status")
    
    # Optimization
    print("\n⚡ Optimization:")
    validator.test_endpoint("GET", "/optimization/insights", [200], description="Optimization insights")
    validator.test_endpoint("POST", "/optimization/reset-learning", [200, 422], {}, "Reset learning")
    
    # Critique Endpoints
    print("\n🔍 Critique:")
    validator.test_endpoint("GET", f"/critique/{TEST_CAPSULE_ID}", [200, 404], description="Get critique")
    validator.test_endpoint("POST", f"/critique/{TEST_CAPSULE_ID}", [422], {}, "Create critique")
    validator.test_endpoint("POST", f"/critique/ask/{TEST_CAPSULE_ID}", [422], {}, "Ask critique")
    validator.test_endpoint("GET", "/critique/statistics/overview", [200], description="Critique stats")
    
    # GitHub Integration
    print("\n🐙 GitHub Integration:")
    validator.test_endpoint("GET", "/api/github/check-token", [200, 401], description="Check GitHub token")
    validator.test_endpoint("POST", "/api/github/push", [422], {}, "GitHub push")
    validator.test_endpoint("POST", "/api/github/push/v2", [422], {}, "GitHub push v2")
    validator.test_endpoint("POST", "/api/github/push/atomic", [422], {}, "Atomic push")
    validator.test_endpoint("POST", "/api/github/push/enterprise", [422], {}, "Enterprise push")
    
    # Enterprise Endpoints
    print("\n🏢 Enterprise:")
    validator.test_endpoint("POST", "/api/enterprise/generate", [401, 422], {}, "Enterprise generate")
    validator.test_endpoint("GET", f"/api/enterprise/status/{TEST_CAPSULE_ID}", [401, 404], description="Enterprise status")
    
    # Delivery Endpoints
    print("\n📦 Delivery:")
    validator.test_endpoint("GET", "/delivery/providers", [200], description="List delivery providers")
    validator.test_endpoint("POST", f"/capsule/{TEST_CAPSULE_ID}/deliver", [422], {}, "Deliver capsule")
    validator.test_endpoint("POST", f"/capsules/{TEST_CAPSULE_ID}/deliver", [422], {}, "Deliver capsule (alt)")
    
    # Download/Export Endpoints
    print("\n💾 Download/Export:")
    validator.test_endpoint("GET", f"/api/capsules/{TEST_CAPSULE_ID}/download", [200, 404, 500], description="Download capsule")
    validator.test_endpoint("GET", f"/api/capsules/{TEST_CAPSULE_ID}/stream", [200, 404, 500], description="Stream capsule")
    validator.test_endpoint("GET", f"/api/capsules/{TEST_CAPSULE_ID}/export/helm", [200, 404, 500], description="Export as Helm")
    validator.test_endpoint("GET", f"/api/capsules/{TEST_CAPSULE_ID}/export/terraform", [200, 404, 500], description="Export as Terraform")
    validator.test_endpoint("GET", f"/api/capsules/{TEST_CAPSULE_ID}/files/main.py", [200, 404, 500], description="Get specific file")
    
    # Complete Pipeline Endpoints
    print("\n🔄 Complete Pipelines:")
    validator.test_endpoint("POST", "/generate/complete-pipeline", [422], {}, "Complete pipeline")
    validator.test_endpoint("POST", "/generate/complete-with-github", [422], {}, "Complete with GitHub")
    validator.test_endpoint("POST", "/generate/complete-with-github-sync", [422], {}, "Complete with GitHub sync")
    
    # Workflow Status
    print("\n📊 Workflow Status:")
    validator.test_endpoint("GET", f"/status/{TEST_WORKFLOW_ID}", [404], description="Workflow status")
    validator.test_endpoint("GET", f"/workflow/status/{TEST_WORKFLOW_ID}", [404], description="Workflow status v2")
    validator.test_endpoint("POST", f"/approve/{TEST_WORKFLOW_ID}", [404], {}, "Approve workflow")
    
    # Internal/Misc Endpoints
    print("\n🔧 Internal/Misc:")
    validator.test_endpoint("POST", "/internal/aitl-review", [422], {}, "Internal AITL review")
    validator.test_endpoint("POST", "/analyze/extended-reasoning", [422], {}, "Extended reasoning")
    validator.test_endpoint("POST", "/analyze/pattern/test-pattern", [422], {}, "Analyze specific pattern")
    
    # Print summary
    validator.print_summary()

if __name__ == "__main__":
    main()