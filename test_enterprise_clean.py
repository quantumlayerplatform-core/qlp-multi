#!/usr/bin/env python3
"""
Test enterprise-grade use case with performance improvements
Clean version focusing on technical implementation
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

async def test_enterprise_platform():
    """Test comprehensive enterprise platform backend"""
    
    print("\n🏢 Enterprise Use Case: E-Commerce Platform Backend")
    print("=" * 70)
    print("\nBuilding a production-ready e-commerce platform with:")
    print("  • Multiple microservices architecture")
    print("  • High-performance requirements")
    print("  • Production best practices")
    print("=" * 70)
    
    request_data = {
        "tenant_id": "enterprise-demo",
        "user_id": "test-user-001",
        "description": """
        Create a comprehensive e-commerce platform backend with these components:

        1. Product Catalog Service:
           - Product CRUD operations with categories and tags
           - Advanced search with filters (price, category, brand)
           - Inventory management and stock tracking
           - Product recommendations engine
           - Image management with CDN integration

        2. Shopping Cart Service:
           - Cart management with session persistence
           - Price calculation with tax and shipping
           - Discount and coupon application
           - Cart abandonment tracking
           - Wishlist functionality

        3. Order Management Service:
           - Order creation and processing workflow
           - Order status tracking and history
           - Invoice generation
           - Shipping integration
           - Return and refund handling

        4. Customer Service:
           - Customer profile management
           - Address book management
           - Order history and tracking
           - Customer preferences
           - Loyalty points system

        5. Payment Processing Service:
           - Multiple payment gateway integration
           - Payment method management
           - Transaction logging
           - Refund processing
           - PCI compliance measures

        6. Search Service:
           - Full-text product search
           - Faceted search with filters
           - Search suggestions and autocomplete
           - Search analytics
           - Elasticsearch integration

        7. Reviews and Ratings Service:
           - Product reviews and ratings
           - Review moderation workflow
           - Helpful votes system
           - Review analytics
           - Customer Q&A section

        8. Recommendation Engine:
           - Personalized product recommendations
           - Related products
           - Frequently bought together
           - Trending products
           - Machine learning integration

        9. Analytics Dashboard:
           - Sales analytics and reporting
           - Customer behavior tracking
           - Inventory analytics
           - Performance metrics
           - Export functionality

        10. Admin API:
            - Product management interface
            - Order management dashboard
            - Customer management
            - Analytics and reporting
            - System configuration

        Technical specifications:
        - RESTful APIs with FastAPI
        - PostgreSQL database with optimized schemas
        - Redis for caching and sessions
        - Comprehensive test suites
        - Docker containerization
        - API documentation
        - Performance optimizations
        """,
        
        "requirements": """
        Build with these requirements:
        - Clean, maintainable code architecture
        - Comprehensive error handling
        - Unit and integration tests
        - Database migrations
        - API rate limiting
        - Caching strategies
        - Monitoring and logging
        """,
        
        "constraints": {
            "language": "python",
            "framework": "fastapi",
            "database": "postgresql",
            "cache": "redis",
            "testing": "pytest"
        },
        
        "metadata": {
            "project_type": "ecommerce_platform",
            "priority": "high",
            "complexity": "high"
        }
    }
    
    print("\n📤 Submitting e-commerce platform request...")
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
                    
                    # Analyze improvements
                    outputs = final_status.get('outputs', [])
                    if outputs:
                        # Count parallelized tasks
                        task_times = []
                        cached_count = 0
                        
                        for output in outputs:
                            execution = output.get('execution', {})
                            if execution.get('status') == 'completed':
                                exec_time = execution.get('execution_time', 0)
                                task_times.append(exec_time)
                                if execution.get('metadata', {}).get('cached'):
                                    cached_count += 1
                        
                        # Performance analysis
                        print(f"\n🚀 Performance Analysis:")
                        print(f"   • Total tasks: {len(outputs)}")
                        print(f"   • Successful tasks: {len(task_times)}")
                        print(f"   • Cached tasks: {cached_count} ({cached_count/len(outputs)*100:.1f}%)")
                        
                        if task_times:
                            avg_time = sum(task_times) / len(task_times)
                            min_time = min(task_times)
                            max_time = max(task_times)
                            
                            print(f"   • Task execution times:")
                            print(f"     - Average: {avg_time:.2f}s")
                            print(f"     - Minimum: {min_time:.2f}s")
                            print(f"     - Maximum: {max_time:.2f}s")
                        
                        # Estimate sequential time
                        sequential_estimate = sum(task_times) if task_times else 0
                        if sequential_estimate > 0:
                            speedup = sequential_estimate / total_time
                            time_saved = sequential_estimate - total_time
                            
                            print(f"\n   📊 Parallel Execution Benefits:")
                            print(f"     - Sequential estimate: {sequential_estimate:.0f}s ({sequential_estimate/60:.1f} min)")
                            print(f"     - Actual parallel time: {total_time:.0f}s ({total_time/60:.1f} min)")
                            print(f"     - Time saved: {time_saved:.0f}s ({time_saved/60:.1f} min)")
                            print(f"     - Speedup factor: {speedup:.1f}x faster")
                    
                    # Show task breakdown by complexity
                    print(f"\n📋 Task Breakdown:")
                    complexity_counts = {"simple": 0, "medium": 0, "complex": 0, "meta": 0}
                    
                    for output in outputs:
                        task_id = output.get('task_id', '')
                        # Infer complexity from task_id or metadata
                        if 'crud' in task_id.lower() or 'endpoint' in task_id.lower():
                            complexity_counts['simple'] += 1
                        elif 'service' in task_id.lower() or 'integration' in task_id.lower():
                            complexity_counts['medium'] += 1
                        elif 'engine' in task_id.lower() or 'analytics' in task_id.lower():
                            complexity_counts['complex'] += 1
                        else:
                            complexity_counts['simple'] += 1
                    
                    for complexity, count in complexity_counts.items():
                        if count > 0:
                            print(f"   • {complexity.capitalize()} tasks: {count}")
                    
                    # Delivery info
                    if final_status.get('capsule_id'):
                        print(f"\n📦 Deliverables:")
                        print(f"   • Capsule ID: {final_status.get('capsule_id')}")
                        print(f"   • Delivery ready: {'Yes' if final_status.get('delivery_ready') else 'No'}")
                        print(f"   • Download: POST /capsules/{final_status.get('capsule_id')}/deliver")
                    
                    print(f"\n🎉 Enterprise platform generated successfully!")
                    print(f"   Complex multi-service architecture completed in {total_time/60:.1f} minutes")
                    print(f"   with {speedup:.1f}x speedup from parallel execution and caching.")
                    
                else:
                    print(f"\n❌ Workflow failed!")
                    print(f"   Status: {final_status.get('status')}")
                    errors = final_status.get('errors', [])
                    if errors:
                        print(f"   Errors:")
                        for error in errors[:3]:  # Show first 3 errors
                            print(f"     • {error}")
                
            else:
                print(f"\n❌ Failed to start workflow!")
                print(f"   Status code: {response.status_code}")
                error_detail = response.text
                try:
                    error_json = json.loads(error_detail)
                    print(f"   Error: {error_json.get('error', 'Unknown error')}")
                    print(f"   Detail: {error_json.get('detail', '')}")
                except:
                    print(f"   Response: {error_detail[:200]}")
                
        except Exception as e:
            print(f"\n❌ Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()

async def main():
    """Run the enterprise test"""
    print("\n🔧 Quantum Layer Platform - Enterprise Performance Test")
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
    await test_enterprise_platform()

if __name__ == "__main__":
    asyncio.run(main())