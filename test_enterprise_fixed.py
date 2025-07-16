#!/usr/bin/env python3
"""
Test enterprise-grade code generation with fixed worker
"""
import requests
import json
import time
import sys

def test_enterprise_workflow():
    """Test with an enterprise-grade application"""
    
    # Enterprise-grade request: Complete microservices application
    request_data = {
        "description": "Create a production-ready inventory management microservices system",
        "requirements": """
        Build a complete inventory management system with:
        1. Product Service (Go) - CRUD operations for products with PostgreSQL
        2. Inventory Service (Python FastAPI) - Stock tracking, reservations, adjustments
        3. Order Service (Node.js Express) - Order processing with inventory checks
        4. API Gateway (Go) - Route requests, auth, rate limiting
        5. Message Queue Integration - RabbitMQ for async communication
        6. Docker Compose setup with all services
        7. Comprehensive unit and integration tests
        8. GitHub Actions CI/CD pipeline
        9. Monitoring with Prometheus and Grafana
        10. API documentation with OpenAPI/Swagger
        """,
        "constraints": {
            "code_quality": "Production-ready with proper error handling",
            "security": "Implement authentication and authorization",
            "logging": "Structured logging with correlation IDs",
            "testing": "Minimum 80% code coverage"
        },
        "tenant_id": "test-tenant",
        "user_id": "test-user"
    }
    
    print("🚀 Testing Enterprise Inventory Management System Generation")
    print("=" * 80)
    
    # Start workflow
    response = requests.post(
        "http://localhost:8000/execute",
        json=request_data,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start workflow: {response.status_code}")
        print(response.text)
        return
    
    workflow_data = response.json()
    workflow_id = workflow_data.get("workflow_id")
    request_id = workflow_data.get("request_id")
    
    print(f"✅ Workflow started successfully!")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   Request ID: {request_id}")
    print("\n⏳ Monitoring workflow progress...")
    
    # Monitor workflow with timeout
    start_time = time.time()
    max_duration = 1800  # 30 minutes for enterprise workflow
    check_interval = 10
    
    last_completed = 0
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_duration:
            print(f"\n⏱️  Workflow timeout after {elapsed:.1f} seconds")
            break
        
        try:
            status_response = requests.get(
                f"http://localhost:8000/workflow/status/{workflow_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                # Show progress
                completed = status_data.get("tasks_completed", 0)
                total = status_data.get("tasks_total", 0)
                status = status_data.get("status", "unknown")
                
                if completed > last_completed:
                    print(f"\n📊 Progress: {completed}/{total} tasks completed ({status})")
                    last_completed = completed
                    
                    # Show completed tasks
                    for output in status_data.get("outputs", []):
                        if output.get("status") == "completed":
                            task_id = output.get("task_id", "unknown")
                            print(f"   ✅ Task {task_id} completed")
                
                # Check if workflow completed
                if status in ["completed", "failed"]:
                    print(f"\n{'✅' if status == 'completed' else '❌'} Workflow {status}!")
                    print(f"⏱️  Total time: {elapsed:.1f} seconds")
                    
                    if status == "completed":
                        print(f"\n📦 Capsule ID: {status_data.get('capsule_id')}")
                        
                        # Show summary
                        print("\n📋 Summary:")
                        print(f"   Tasks completed: {completed}/{total}")
                        print(f"   Success rate: {(completed/total)*100:.1f}%")
                        
                        # Show generated components
                        print("\n🔧 Generated Components:")
                        outputs = status_data.get("outputs", [])
                        for output in outputs:
                            if output.get("status") == "completed":
                                desc = output.get("description", "")
                                print(f"   • {desc}")
                    
                    return status_data
            
        except Exception as e:
            print(f"\n⚠️  Error checking status: {str(e)}")
        
        # Show heartbeat
        if int(elapsed) % 30 == 0:
            print(".", end="", flush=True)
        
        time.sleep(check_interval)
    
    return None

if __name__ == "__main__":
    print("🏢 Enterprise-Grade Code Generation Test")
    print("=" * 80)
    print("Testing with production-ready microservices architecture")
    print()
    
    result = test_enterprise_workflow()
    
    if result:
        print("\n✅ Test completed!")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ Test failed or timed out")
        sys.exit(1)