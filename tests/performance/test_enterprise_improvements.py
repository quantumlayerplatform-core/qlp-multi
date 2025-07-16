#!/usr/bin/env python3
"""
Test enterprise-grade use case with performance improvements
Real-world scenario: Multi-tenant SaaS Platform Backend
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Base URL for orchestrator
BASE_URL = "http://localhost:8000"

async def monitor_workflow_progress(workflow_id: str, client: httpx.AsyncClient):
    """Monitor and display real-time workflow progress"""
    last_completed = 0
    start_monitor = time.time()
    
    while True:
        try:
            response = await client.get(f"{BASE_URL}/workflow/status/{workflow_id}")
            if response.status_code == 200:
                status = response.json()
                completed = status.get('tasks_completed', 0)
                total = status.get('tasks_total', 0)
                
                # Show progress update
                if completed > last_completed:
                    elapsed = time.time() - start_monitor
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (total - completed) / rate if rate > 0 else 0
                    
                    print(f"\r⏳ Progress: {completed}/{total} tasks "
                          f"({completed/total*100:.1f}%) "
                          f"| Rate: {rate:.1f} tasks/sec "
                          f"| ETA: {eta:.0f}s", end="", flush=True)
                    
                    last_completed = completed
                
                # Check completion
                if status.get('status') in ['completed', 'failed']:
                    print()  # New line after progress
                    return status
                    
        except Exception as e:
            print(f"\n⚠️  Monitoring error: {e}")
            
        await asyncio.sleep(2)

async def test_enterprise_saas_platform():
    """Test comprehensive multi-tenant SaaS platform backend"""
    
    print("\n🏢 Enterprise Use Case: Multi-Tenant SaaS Platform Backend")
    print("=" * 70)
    print("\nThis represents a real-world enterprise application with:")
    print("  • Multiple microservices")
    print("  • Complex interdependencies")
    print("  • Security-critical components")
    print("  • High scalability requirements")
    print("=" * 70)
    
    request_data = {
        "tenant_id": "enterprise-test",
        "user_id": "test-user-001",
        "description": """
        Create a complete multi-tenant SaaS platform backend with the following components:

        1. **Authentication & Authorization Service**
           - Multi-tenant user authentication with JWT tokens
           - OAuth2 integration (Google, GitHub, Microsoft)
           - Role-based access control (RBAC) with tenant isolation
           - API key management for service-to-service auth
           - Session management with Redis
           - Two-factor authentication (2FA) support

        2. **Tenant Management Service**
           - Tenant registration and onboarding
           - Subscription management with different tiers
           - Usage tracking and billing integration
           - Tenant-specific configuration management
           - Data isolation and multi-tenancy patterns

        3. **User Management Service**
           - User CRUD operations with tenant scoping
           - User profile management
           - Team/organization management
           - Invitation system for adding team members
           - Activity logging and audit trails

        4. **API Gateway Service**
           - Request routing and load balancing
           - Rate limiting per tenant/user
           - API versioning support
           - Request/response transformation
           - Circuit breaker implementation
           - Metrics and monitoring integration

        5. **Notification Service**
           - Email notifications (SendGrid integration)
           - In-app notifications
           - Push notifications
           - Webhook delivery system
           - Template management
           - Notification preferences per user

        6. **File Storage Service**
           - Multi-tenant file upload/download
           - S3-compatible storage integration
           - File metadata management
           - Access control and sharing
           - Virus scanning integration
           - CDN integration for static assets

        7. **Analytics Service**
           - Usage analytics per tenant
           - Custom event tracking
           - Report generation
           - Data export functionality
           - Real-time dashboards
           - Predictive analytics

        8. **Admin Dashboard API**
           - System health monitoring
           - Tenant management interface
           - User impersonation for support
           - System configuration management
           - Deployment management
           - Audit log viewer

        9. **Integration Service**
           - Webhook management
           - Third-party API integrations
           - Data synchronization
           - ETL pipelines
           - Event streaming (Kafka integration)

        10. **Background Job Service**
            - Async task processing with Celery
            - Scheduled jobs with cron-like syntax
            - Job monitoring and retry logic
            - Priority queues
            - Dead letter queue handling

        Technical Requirements:
        - Use Python with FastAPI for all services
        - PostgreSQL with proper migrations for each service
        - Redis for caching and session storage
        - Docker and docker-compose setup
        - Kubernetes manifests for production deployment
        - Comprehensive unit and integration tests (pytest)
        - API documentation with OpenAPI/Swagger
        - Monitoring with Prometheus metrics
        - Centralized logging setup
        - CI/CD pipeline configuration (GitHub Actions)
        - Security best practices (OWASP compliance)
        - Performance optimization (caching, indexing)
        - Horizontal scalability support
        - Data backup and disaster recovery procedures
        """,
        
        "requirements": """
        - Production-ready code with proper error handling
        - Comprehensive test coverage (>80%)
        - Security-first design with threat modeling
        - Performance optimized for 10k+ concurrent users
        - Multi-region deployment support
        - GDPR compliance for data handling
        - API rate limiting and DDoS protection
        - Zero-downtime deployment strategy
        """,
        
        "constraints": {
            "language": "python",
            "framework": "fastapi",
            "database": "postgresql",
            "cache": "redis",
            "container": "docker",
            "orchestration": "kubernetes",
            "testing": "pytest",
            "ci_cd": "github_actions"
        },
        
        "metadata": {
            "project_type": "enterprise_saas",
            "priority": "critical",
            "estimated_complexity": "very_high",
            "target_scale": "10k_users",
            "compliance": ["GDPR", "SOC2", "HIPAA"]
        }
    }
    
    print("\n📤 Submitting enterprise SaaS platform request...")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=1200.0) as client:  # 20 min timeout
        try:
            # Submit request
            response = await client.post(
                f"{BASE_URL}/execute",
                json=request_data
            )
            
            if response.status_code == 202:
                result = response.json()
                workflow_id = result.get("workflow_id")
                print(f"\n✅ Workflow initiated successfully!")
                print(f"   Workflow ID: {workflow_id}")
                print(f"   Status URL: {BASE_URL}/workflow/status/{workflow_id}")
                
                print("\n📊 Monitoring execution progress...")
                print("   (Real-time updates will appear below)")
                print("-" * 70)
                
                # Monitor progress
                final_status = await monitor_workflow_progress(workflow_id, client)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                print("\n" + "=" * 70)
                print("📈 EXECUTION SUMMARY")
                print("=" * 70)
                
                if final_status.get("status") == "completed":
                    print(f"\n✅ Workflow completed successfully!")
                    print(f"\n⏱️  Performance Metrics:")
                    print(f"   • Total execution time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
                    print(f"   • Tasks completed: {final_status.get('tasks_completed')}/{final_status.get('tasks_total')}")
                    print(f"   • Average time per task: {total_time/final_status.get('tasks_completed', 1):.2f} seconds")
                    
                    # Show task breakdown
                    outputs = final_status.get('outputs', [])
                    if outputs:
                        print(f"\n📋 Task Execution Details:")
                        
                        # Group by status
                        completed_tasks = []
                        failed_tasks = []
                        
                        for output in outputs:
                            task_id = output.get('task_id', 'unknown')
                            execution = output.get('execution', {})
                            status = execution.get('status', 'unknown')
                            exec_time = execution.get('execution_time', 0)
                            cached = execution.get('metadata', {}).get('cached', False)
                            
                            task_info = {
                                'id': task_id,
                                'time': exec_time,
                                'cached': cached,
                                'tier': execution.get('agent_tier_used', 'unknown')
                            }
                            
                            if status == 'completed':
                                completed_tasks.append(task_info)
                            else:
                                failed_tasks.append(task_info)
                        
                        # Show completed tasks
                        print(f"\n   ✅ Completed Tasks ({len(completed_tasks)}):")
                        for task in sorted(completed_tasks, key=lambda x: x['time'])[:10]:
                            cache_indicator = "💾" if task['cached'] else "🔨"
                            print(f"      {cache_indicator} {task['id']}: {task['time']:.1f}s (Tier: {task['tier']})")
                        if len(completed_tasks) > 10:
                            print(f"      ... and {len(completed_tasks) - 10} more")
                        
                        # Show failed tasks if any
                        if failed_tasks:
                            print(f"\n   ❌ Failed Tasks ({len(failed_tasks)}):")
                            for task in failed_tasks[:5]:
                                print(f"      • {task['id']}")
                    
                    # Performance improvements analysis
                    print(f"\n🚀 Performance Improvements Analysis:")
                    
                    # Check for parallel execution
                    metadata = final_status.get('metadata', {})
                    if 'execution_batches' in metadata:
                        print(f"   • Parallel Execution: ✅ Enabled")
                        print(f"     - Execution batches: {metadata.get('execution_batches', 'N/A')}")
                        print(f"     - Avg batch size: {metadata.get('avg_batch_size', 'N/A')}")
                    
                    # Check for caching
                    cache_hits = sum(1 for output in outputs 
                                   if output.get('execution', {}).get('metadata', {}).get('cached', False))
                    if cache_hits > 0:
                        cache_rate = (cache_hits / len(outputs)) * 100 if outputs else 0
                        print(f"   • Caching: ✅ Active")
                        print(f"     - Cache hits: {cache_hits}/{len(outputs)} ({cache_rate:.1f}%)")
                    
                    # Estimate time saved
                    if final_status.get('tasks_total', 0) > 10:
                        sequential_estimate = final_status.get('tasks_total', 0) * 30  # 30s per task estimate
                        time_saved = sequential_estimate - total_time
                        speedup = sequential_estimate / total_time if total_time > 0 else 1
                        
                        print(f"\n   📊 Estimated Performance Gain:")
                        print(f"     - Sequential estimate: {sequential_estimate:.0f}s ({sequential_estimate/60:.1f} min)")
                        print(f"     - Actual time: {total_time:.0f}s ({total_time/60:.1f} min)")
                        print(f"     - Time saved: {time_saved:.0f}s ({time_saved/60:.1f} min)")
                        print(f"     - Speedup factor: {speedup:.1f}x faster")
                    
                    # Capsule information
                    if final_status.get('capsule_id'):
                        print(f"\n📦 Deliverables:")
                        print(f"   • Capsule ID: {final_status.get('capsule_id')}")
                        print(f"   • Status: {'Ready for delivery' if final_status.get('delivery_ready') else 'Processing'}")
                        
                        if final_status.get('github_url'):
                            print(f"   • GitHub Repository: {final_status.get('github_url')}")
                    
                    print(f"\n🎉 Enterprise SaaS platform generated successfully!")
                    print(f"   This complex multi-service architecture was completed in just {total_time/60:.1f} minutes")
                    print(f"   thanks to parallel execution, intelligent caching, and optimized workflows.")
                    
                else:
                    print(f"\n❌ Workflow failed!")
                    print(f"   Status: {final_status.get('status')}")
                    print(f"   Errors: {json.dumps(final_status.get('errors', []), indent=2)}")
                
            else:
                print(f"\n❌ Failed to start workflow!")
                print(f"   Status code: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()

async def main():
    """Run the enterprise test"""
    print("\n🔧 Quantum Layer Platform - Enterprise Performance Test")
    print("=" * 70)
    print("Testing with real-world enterprise use case:")
    print("  • Multi-tenant SaaS platform")
    print("  • 10+ microservices")
    print("  • Complex interdependencies")
    print("  • Production-grade requirements")
    print("=" * 70)
    
    # Check service health first
    print("\n🏥 Checking service health...")
    services_ok = True
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, port in [
            ("Orchestrator", 8000),
            ("Agent Factory", 8001),
            ("Validation Mesh", 8002),
            ("Vector Memory", 8003),
            ("Execution Sandbox", 8004)
        ]:
            try:
                response = await client.get(f"http://localhost:{port}/health")
                if response.status_code == 200:
                    print(f"   ✅ {service} is healthy")
                else:
                    print(f"   ❌ {service} is not healthy")
                    services_ok = False
            except:
                print(f"   ❌ {service} is not responding")
                services_ok = False
    
    if not services_ok:
        print("\n⚠️  Some services are not healthy. Please run: ./start_all.sh")
        return
    
    print("\n✅ All services are healthy! Starting test...")
    
    # Run the test
    await test_enterprise_saas_platform()

if __name__ == "__main__":
    asyncio.run(main())