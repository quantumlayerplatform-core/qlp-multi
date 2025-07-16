#!/usr/bin/env python3
"""
Enterprise-scale testing for Quantum Layer Platform
Tests complex, multi-language, multi-domain projects
"""
import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import random

# Test configurations for different project complexities
ENTERPRISE_TEST_CASES = [
    {
        "name": "Enterprise E-commerce Platform",
        "description": """
        Build a complete enterprise e-commerce platform with microservices architecture:
        - User authentication and authorization service (Node.js)
        - Product catalog service with search (Python/FastAPI)
        - Shopping cart and checkout service (Go)
        - Payment processing integration (Java/Spring Boot)
        - Order management system (Python)
        - Real-time inventory tracking (Node.js/Socket.io)
        - Admin dashboard (React/TypeScript)
        - Mobile apps (React Native)
        - Message queue integration (RabbitMQ)
        - Caching layer (Redis)
        - Database design (PostgreSQL, MongoDB)
        - CI/CD pipelines
        - Kubernetes deployment configs
        - Monitoring and logging setup
        - API documentation
        - Load testing scripts
        - Security implementations (OAuth2, JWT, rate limiting)
        """,
        "expected_tasks": 25,
        "complexity": "very_complex",
        "languages": ["python", "javascript", "go", "java", "typescript"],
        "timeout_minutes": 30
    },
    {
        "name": "AI-Powered Analytics Platform",
        "description": """
        Create an AI-powered business analytics platform:
        - Data ingestion pipeline supporting multiple formats (Python)
        - ETL processes with Apache Airflow
        - Machine learning model training service (Python/TensorFlow)
        - Model serving API (Python/FastAPI)
        - Real-time data streaming (Apache Kafka, Scala)
        - Analytics dashboard (React/D3.js)
        - Natural language query interface (Python/LangChain)
        - Data warehouse design (Snowflake/BigQuery)
        - Feature store implementation
        - A/B testing framework
        - Jupyter notebook integration
        - Model monitoring and drift detection
        - Automated reporting system
        - API gateway with authentication
        - Comprehensive test suites
        - Documentation and tutorials
        """,
        "expected_tasks": 20,
        "complexity": "very_complex",
        "languages": ["python", "scala", "javascript", "sql"],
        "timeout_minutes": 25
    },
    {
        "name": "Banking Core System",
        "description": """
        Develop a modern banking core system:
        - Account management service (Java/Spring Boot)
        - Transaction processing engine (Go)
        - Fraud detection system (Python/ML)
        - Customer portal (Angular/TypeScript)
        - Mobile banking app (Flutter)
        - Regulatory compliance module (Java)
        - Audit logging system
        - Batch processing for statements
        - Integration with payment networks
        - Risk assessment engine
        - KYC/AML implementation
        - Database encryption and security
        - Disaster recovery setup
        - Performance testing framework
        - API documentation with OpenAPI
        - Monitoring dashboards
        """,
        "expected_tasks": 22,
        "complexity": "very_complex",
        "languages": ["java", "go", "python", "typescript", "dart"],
        "timeout_minutes": 30
    },
    {
        "name": "IoT Platform",
        "description": """
        Build a comprehensive IoT platform:
        - Device management service (Go)
        - MQTT broker integration (Python)
        - Real-time data processing (Apache Flink/Java)
        - Time-series database setup (InfluxDB)
        - Analytics engine (Python/Spark)
        - Web dashboard (Vue.js)
        - Mobile app for device control (React Native)
        - Edge computing framework (Rust)
        - Security layer with device authentication
        - Firmware update system
        - Alert and notification service
        - API gateway
        - Load balancing setup
        - Containerization with Docker
        - Kubernetes orchestration
        - Comprehensive testing
        """,
        "expected_tasks": 18,
        "complexity": "complex",
        "languages": ["go", "python", "java", "javascript", "rust"],
        "timeout_minutes": 20
    },
    {
        "name": "Healthcare Management System",
        "description": """
        Create a HIPAA-compliant healthcare management system:
        - Patient management system (C#/.NET)
        - Electronic health records (Python/Django)
        - Appointment scheduling (Node.js)
        - Telemedicine platform (WebRTC/JavaScript)
        - Prescription management (Java)
        - Billing and insurance processing (Python)
        - Lab results integration
        - Medical imaging viewer (JavaScript/DICOM)
        - Mobile apps for patients and doctors (React Native)
        - Reporting and analytics
        - HIPAA compliance implementation
        - Audit trails
        - Backup and recovery
        - API security
        - Integration tests
        - User documentation
        """,
        "expected_tasks": 20,
        "complexity": "very_complex",
        "languages": ["csharp", "python", "javascript", "java"],
        "timeout_minutes": 25
    }
]

class EnterpriseTestRunner:
    """Runs enterprise-scale tests"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case"""
        print(f"\n{'='*80}")
        print(f"Running Test: {test_case['name']}")
        print(f"Expected Complexity: {test_case['complexity']}")
        print(f"Expected Languages: {', '.join(test_case['languages'])}")
        print(f"Expected Tasks: ~{test_case['expected_tasks']}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        try:
            # Submit request
            async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0)) as client:
                # Start workflow
                print("📤 Submitting request to platform...")
                response = await client.post(
                    f"{self.base_url}/execute",
                    json={
                        "description": test_case["description"],
                        "requirements": {
                            "project_name": test_case["name"].lower().replace(" ", "_"),
                            "complexity": test_case["complexity"],
                            "expected_languages": test_case["languages"],
                            "enterprise_features": True
                        },
                        "constraints": {
                            "timeout_minutes": test_case["timeout_minutes"],
                            "quality_threshold": 0.8,
                            "include_tests": True,
                            "include_documentation": True,
                            "include_ci_cd": True
                        },
                        "metadata": {
                            "test_case": test_case["name"],
                            "test_run_id": f"enterprise_test_{int(time.time())}"
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to start workflow: {response.text}")
                
                result = response.json()
                workflow_id = result.get("workflow_id")
                print(f"✅ Workflow started: {workflow_id}")
                
                # Poll for completion
                print("\n⏳ Waiting for completion...")
                poll_count = 0
                max_polls = test_case["timeout_minutes"] * 6  # Poll every 10 seconds
                
                while poll_count < max_polls:
                    await asyncio.sleep(10)
                    poll_count += 1
                    
                    status_response = await client.get(
                        f"{self.base_url}/workflow/status/{workflow_id}"
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status")
                        
                        # Print progress
                        tasks_completed = status_data.get("tasks_completed", 0)
                        tasks_total = status_data.get("tasks_total", 0)
                        
                        if tasks_total > 0:
                            progress = (tasks_completed / tasks_total) * 100
                            print(f"\r📊 Progress: {tasks_completed}/{tasks_total} tasks "
                                  f"({progress:.1f}%) - Status: {status}", end="", flush=True)
                        
                        if status in ["completed", "failed", "cancelled"]:
                            print()  # New line after progress
                            return await self._analyze_results(
                                test_case, 
                                workflow_id, 
                                status_data, 
                                time.time() - start_time
                            )
                
                # Timeout
                print("\n❌ Test timed out")
                return {
                    "test_case": test_case["name"],
                    "status": "timeout",
                    "execution_time": time.time() - start_time,
                    "error": f"Workflow did not complete within {test_case['timeout_minutes']} minutes"
                }
                
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            return {
                "test_case": test_case["name"],
                "status": "error",
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def _analyze_results(self, test_case: Dict[str, Any], workflow_id: str, 
                              status_data: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Analyze test results"""
        print(f"\n📈 Analyzing results for {test_case['name']}...")
        
        # Extract metrics
        tasks_total = status_data.get("tasks_total", 0)
        tasks_completed = status_data.get("tasks_completed", 0)
        success_rate = status_data.get("success_rate", 0)
        detected_language = status_data.get("detected_language", "unknown")
        
        # Check outputs
        outputs = status_data.get("outputs", [])
        languages_used = set()
        task_types = {}
        errors = []
        
        for output in outputs:
            if output.get("status") == "completed":
                lang = output.get("metadata", {}).get("language", "unknown")
                languages_used.add(lang)
                
                task_type = output.get("output_type", "unknown")
                task_types[task_type] = task_types.get(task_type, 0) + 1
            else:
                errors.append({
                    "task_id": output.get("task_id"),
                    "error": output.get("error_details", "Unknown error")
                })
        
        # Validate results
        validations = {
            "task_count": {
                "expected": test_case["expected_tasks"],
                "actual": tasks_total,
                "passed": abs(tasks_total - test_case["expected_tasks"]) <= 5
            },
            "completion_rate": {
                "expected": 0.8,
                "actual": success_rate,
                "passed": success_rate >= 0.8
            },
            "languages": {
                "expected": set(test_case["languages"]),
                "actual": languages_used,
                "passed": len(languages_used.intersection(test_case["languages"])) >= len(test_case["languages"]) * 0.7
            },
            "execution_time": {
                "expected": test_case["timeout_minutes"] * 60,
                "actual": execution_time,
                "passed": execution_time < test_case["timeout_minutes"] * 60
            }
        }
        
        # Calculate overall pass/fail
        all_passed = all(v["passed"] for v in validations.values())
        
        # Get capsule info
        capsule_id = status_data.get("capsule_id")
        github_info = status_data.get("github", {})
        
        result = {
            "test_case": test_case["name"],
            "workflow_id": workflow_id,
            "status": "passed" if all_passed else "failed",
            "execution_time": execution_time,
            "tasks": {
                "total": tasks_total,
                "completed": tasks_completed,
                "success_rate": success_rate
            },
            "languages": {
                "expected": test_case["languages"],
                "detected": list(languages_used),
                "primary": detected_language
            },
            "task_types": task_types,
            "validations": validations,
            "errors": errors,
            "capsule_id": capsule_id,
            "github": github_info,
            "metrics": status_data.get("metrics", {})
        }
        
        # Print summary
        print(f"\n📋 Test Summary:")
        print(f"  - Status: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        print(f"  - Tasks: {tasks_completed}/{tasks_total} completed ({success_rate:.1%} success rate)")
        print(f"  - Languages: {', '.join(languages_used)}")
        print(f"  - Execution Time: {execution_time:.1f}s")
        
        if capsule_id:
            print(f"  - Capsule ID: {capsule_id}")
        
        if github_info:
            print(f"  - GitHub: {github_info.get('html_url', 'N/A')}")
        
        if errors:
            print(f"  - Errors: {len(errors)} tasks failed")
        
        return result
    
    async def run_all_tests(self, test_indices: List[int] = None):
        """Run all or selected test cases"""
        print("\n🚀 Starting Enterprise Scale Testing")
        print(f"   Platform URL: {self.base_url}")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        
        # Select test cases
        if test_indices:
            test_cases = [ENTERPRISE_TEST_CASES[i] for i in test_indices 
                         if i < len(ENTERPRISE_TEST_CASES)]
        else:
            test_cases = ENTERPRISE_TEST_CASES
        
        print(f"   Running {len(test_cases)} test cases")
        
        # Run tests
        for i, test_case in enumerate(test_cases):
            print(f"\n\n🧪 Test Case {i+1}/{len(test_cases)}")
            result = await self.run_test_case(test_case)
            self.results.append(result)
            
            # Brief pause between tests
            if i < len(test_cases) - 1:
                print("\n⏸️  Pausing 30 seconds before next test...")
                await asyncio.sleep(30)
        
        # Print final summary
        self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final test summary"""
        print("\n\n" + "="*80)
        print("ENTERPRISE TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.results if r.get("status") == "passed")
        total = len(self.results)
        
        print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        print("\nIndividual Results:")
        for i, result in enumerate(self.results):
            status_icon = "✅" if result.get("status") == "passed" else "❌"
            print(f"\n{i+1}. {result['test_case']}: {status_icon} {result['status'].upper()}")
            
            if result.get("tasks"):
                print(f"   - Tasks: {result['tasks']['completed']}/{result['tasks']['total']} "
                      f"({result['tasks']['success_rate']:.1%} success)")
            
            if result.get("execution_time"):
                print(f"   - Time: {result['execution_time']:.1f}s")
            
            if result.get("error"):
                print(f"   - Error: {result['error']}")
            
            if result.get("capsule_id"):
                print(f"   - Capsule: {result['capsule_id']}")
        
        # Save results
        with open(f"enterprise_test_results_{int(time.time())}.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📁 Full results saved to enterprise_test_results_*.json")

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run enterprise scale tests")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Orchestrator URL")
    parser.add_argument("--test", type=int, nargs="+", 
                       help="Specific test indices to run (0-based)")
    
    args = parser.parse_args()
    
    runner = EnterpriseTestRunner(args.url)
    await runner.run_all_tests(args.test)

if __name__ == "__main__":
    asyncio.run(main())