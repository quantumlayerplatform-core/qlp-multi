#!/usr/bin/env python3
"""
Test the /execute endpoint with enterprise-scale request
"""
import httpx
import json
import asyncio
import time
from datetime import datetime

async def test_execute():
    """Test the execute endpoint with a complex multi-language project"""
    
    # Complex enterprise request
    request_data = {
        "tenant_id": "enterprise-test",
        "user_id": "test-user",
        "description": """
        Build a modern fintech payment processing platform with the following components:
        
        1. Payment Gateway API (Go) - High-performance REST API for payment processing
           - Support for credit cards, ACH, wire transfers
           - PCI DSS compliant implementation
           - Rate limiting and fraud detection
           
        2. Transaction Processing Engine (Java/Spring Boot)
           - Async transaction processing with Kafka
           - Database transactions with PostgreSQL
           - Integration with multiple payment providers
           
        3. Risk Assessment Service (Python)
           - Machine learning fraud detection
           - Real-time risk scoring
           - Historical analysis and reporting
           
        4. Customer Portal (React/TypeScript)
           - Modern responsive UI
           - Real-time transaction status
           - Multi-factor authentication
           
        5. Mobile SDKs (Swift for iOS, Kotlin for Android)
           - Secure payment collection
           - Biometric authentication
           - Offline transaction queueing
           
        6. Admin Dashboard (Vue.js)
           - Transaction monitoring
           - Risk management interface
           - Customer support tools
           
        7. Reporting Service (Python/Pandas)
           - Daily settlement reports
           - Compliance reporting
           - Business intelligence dashboards
           
        8. Infrastructure
           - Docker containers for all services
           - Kubernetes deployment manifests
           - CI/CD pipelines with GitHub Actions
           - Terraform for AWS infrastructure
           - Monitoring with Prometheus/Grafana
           
        Include comprehensive test suites, API documentation, security implementations,
        and production-ready configurations.
        """,
        "requirements": """Enterprise-grade fintech platform with microservices architecture, 
        multi-language support, comprehensive testing, security focus, and cloud-native deployment""",
        "constraints": {
            "quality_threshold": 0.85,
            "max_execution_time_minutes": 30
        },
        "metadata": {
            "request_type": "enterprise_test",
            "timestamp": datetime.now().isoformat(),
            "project_requirements": {
                "project_name": "fintech_payment_platform",
                "languages": ["go", "java", "python", "typescript", "swift", "kotlin"],
                "include_tests": True,
                "include_documentation": True,
                "include_ci_cd": True,
                "security_focus": True,
                "scalability": "high"
            }
        }
    }
    
    print("🚀 Testing /execute endpoint with enterprise-scale request")
    print(f"📋 Project: Fintech Payment Platform")
    print(f"🔧 Languages: Go, Java, Python, TypeScript, Swift, Kotlin")
    print(f"📦 Expected components: 8+ major services")
    print("-" * 80)
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0)) as client:
        try:
            # Submit the request
            print("\n📤 Submitting request to /execute...")
            start_time = time.time()
            
            response = await client.post(
                "http://localhost:8000/execute",
                json=request_data
            )
            
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return
            
            result = response.json()
            request_id = result.get("request_id")
            workflow_id = result.get("workflow_id")
            
            print(f"✅ Request submitted successfully!")
            print(f"📌 Request ID: {request_id}")
            print(f"🔄 Workflow ID: {workflow_id}")
            
            # Poll for status
            print("\n⏳ Monitoring workflow progress...")
            poll_count = 0
            last_status = None
            
            while True:
                await asyncio.sleep(5)  # Poll every 5 seconds
                poll_count += 1
                
                # Get status
                status_response = await client.get(
                    f"http://localhost:8000/workflow/status/{workflow_id}"
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get("status")
                    
                    # Extract progress info
                    tasks_completed = status_data.get("tasks_completed", 0)
                    tasks_total = status_data.get("tasks_total", 0)
                    running_activities = len(status_data.get("running_activities", []))
                    
                    # Calculate progress
                    progress = (tasks_completed / tasks_total * 100) if tasks_total > 0 else 0
                    elapsed = time.time() - start_time
                    
                    # Print update only if status changed
                    if current_status != last_status or poll_count % 6 == 0:  # Or every 30 seconds
                        print(f"\r⚡ Status: {current_status} | "
                              f"Progress: {tasks_completed}/{tasks_total} ({progress:.1f}%) | "
                              f"Active: {running_activities} | "
                              f"Time: {elapsed:.1f}s", end="", flush=True)
                    
                    last_status = current_status
                    
                    # Check if completed
                    if current_status in ["completed", "failed", "cancelled"]:
                        print()  # New line
                        execution_time = time.time() - start_time
                        
                        print(f"\n{'='*80}")
                        print(f"📊 Workflow {current_status.upper()}")
                        print(f"{'='*80}")
                        
                        # Get detailed results
                        if current_status == "completed":
                            capsule_id = status_data.get("capsule_id")
                            outputs = status_data.get("outputs", [])
                            
                            print(f"\n✅ Successfully completed in {execution_time:.1f} seconds")
                            print(f"📦 Capsule ID: {capsule_id}")
                            print(f"📋 Total tasks: {tasks_total}")
                            print(f"✓ Completed tasks: {tasks_completed}")
                            print(f"📈 Success rate: {status_data.get('success_rate', 0):.1%}")
                            
                            # Analyze outputs by type
                            output_types = {}
                            languages_used = set()
                            for output in outputs:
                                if output.get("status") == "completed":
                                    output_type = output.get("output_type", "unknown")
                                    output_types[output_type] = output_types.get(output_type, 0) + 1
                                    
                                    lang = output.get("metadata", {}).get("language")
                                    if lang:
                                        languages_used.add(lang)
                            
                            print(f"\n🔧 Output breakdown:")
                            for out_type, count in output_types.items():
                                print(f"  - {out_type}: {count}")
                            
                            print(f"\n💻 Languages detected: {', '.join(sorted(languages_used))}")
                            
                            # Check GitHub push
                            github_info = status_data.get("github")
                            if github_info:
                                print(f"\n🐙 GitHub repository: {github_info.get('html_url', 'N/A')}")
                            
                            # Performance metrics
                            metrics = status_data.get("metadata", {}).get("system_metrics", {})
                            if metrics:
                                print(f"\n📊 System metrics:")
                                print(f"  - CPU usage: {metrics.get('cpu_percent', 0):.1f}%")
                                print(f"  - Memory usage: {metrics.get('memory_percent', 0):.1f}%")
                            
                            # Show sample outputs
                            print(f"\n📄 Sample task outputs:")
                            for i, output in enumerate(outputs[:3]):  # First 3 outputs
                                if output.get("status") == "completed":
                                    print(f"\n  Task {i+1}: {output.get('task_id')}")
                                    print(f"    Type: {output.get('output_type')}")
                                    print(f"    Language: {output.get('metadata', {}).get('language')}")
                                    print(f"    Execution time: {output.get('execution_time', 0):.2f}s")
                                    print(f"    Agent tier: {output.get('agent_tier_used')}")
                            
                            # Capsule download info
                            if capsule_id:
                                print(f"\n💾 Download capsule:")
                                print(f"    curl -O http://localhost:8000/api/capsules/{capsule_id}/download?format=zip")
                        
                        else:
                            print(f"\n❌ Workflow {current_status}")
                            print(f"Execution time: {execution_time:.1f} seconds")
                            
                            if status_data.get("error"):
                                print(f"Error: {status_data['error']}")
                            
                            # Show failed tasks
                            outputs = status_data.get("outputs", [])
                            failed_tasks = [o for o in outputs if o.get("status") == "failed"]
                            if failed_tasks:
                                print(f"\n❌ Failed tasks:")
                                for task in failed_tasks[:5]:  # First 5 failures
                                    print(f"  - {task.get('task_id')}: {task.get('error_details', 'Unknown error')}")
                        
                        break
                
                # Timeout after 45 minutes
                if time.time() - start_time > 2700:
                    print(f"\n⏱️ Timeout: Workflow did not complete within 45 minutes")
                    break
            
        except Exception as e:
            print(f"\n❌ Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()

async def main():
    """Main test runner"""
    await test_execute()
    
    print("\n\n💡 Tips:")
    print("  - Check Temporal UI at http://localhost:8088 for workflow details")
    print("  - View logs: docker logs qlp-temporal-worker -f")
    print("  - Monitor metrics at http://localhost:8000/metrics")

if __name__ == "__main__":
    asyncio.run(main())