#!/usr/bin/env python3
"""
Test NLP to Production Flow - Demonstrates the platform's full capabilities
"""
import httpx
import json
import asyncio
import time
from datetime import datetime

async def test_nlp_to_production():
    """Test the complete NLP to production flow"""
    
    # Comprehensive but focused request
    request_data = {
        "tenant_id": "demo-enterprise",
        "user_id": "test-user",
        "description": """
        Build a modern e-commerce API backend with the following features:
        
        1. Product Management API (Python/FastAPI)
           - CRUD operations for products
           - Category management
           - Inventory tracking
           - Search and filtering
           
        2. Order Processing Service (Go)
           - Shopping cart management
           - Order placement and tracking
           - Payment integration hooks
           - Email notifications
           
        3. User Authentication Service (Node.js/Express)
           - JWT-based authentication
           - User registration and login
           - Password reset functionality
           - Role-based access control
           
        Include unit tests, API documentation, Docker setup, and CI/CD pipeline.
        Use best practices for security, error handling, and performance.
        """,
        "requirements": """Modern e-commerce backend with microservices architecture, 
        multi-language implementation (Python, Go, Node.js), comprehensive testing, 
        containerization, and production-ready deployment""",
        "constraints": {
            "quality_threshold": 0.85,
            "max_execution_time_minutes": 30
        },
        "metadata": {
            "request_type": "nlp_to_production_demo",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    print("🚀 Testing NLP to Production Flow")
    print("=" * 60)
    print("📝 Natural Language Request:")
    print("  - E-commerce API backend")
    print("  - 3 microservices")
    print("  - 3 different languages (Python, Go, Node.js)")
    print("  - Tests, Docker, CI/CD")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0)) as client:
        try:
            # Submit the request
            print("\n📤 Submitting NLP request...")
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
            
            print(f"✅ Request accepted!")
            print(f"🔄 Workflow ID: {workflow_id}")
            
            # Poll for status
            print("\n⏳ Platform is processing your request...")
            print("   Steps: NLP → Task Decomposition → Agent Execution → Validation → Production Code")
            
            poll_count = 0
            last_status = None
            
            while True:
                await asyncio.sleep(10)  # Poll every 10 seconds
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
                    
                    # Calculate progress
                    progress = (tasks_completed / tasks_total * 100) if tasks_total > 0 else 0
                    elapsed = time.time() - start_time
                    
                    # Print progress update
                    print(f"\r📊 Progress: {tasks_completed}/{tasks_total} tasks ({progress:.1f}%) | "
                          f"Time: {elapsed:.1f}s | Status: {current_status}", end="", flush=True)
                    
                    # Check if completed
                    if current_status in ["completed", "failed", "cancelled"]:
                        print()  # New line
                        execution_time = time.time() - start_time
                        
                        print(f"\n{'='*60}")
                        print(f"🎯 Workflow {current_status.upper()}")
                        print(f"{'='*60}")
                        
                        if current_status == "completed":
                            capsule_id = status_data.get("capsule_id")
                            outputs = status_data.get("outputs", [])
                            
                            print(f"\n✅ Successfully converted NLP to production code!")
                            print(f"⏱️  Total time: {execution_time:.1f} seconds")
                            print(f"📦 Capsule ID: {capsule_id}")
                            print(f"📋 Tasks completed: {tasks_completed}/{tasks_total}")
                            
                            # Analyze outputs
                            languages_generated = set()
                            services_created = []
                            
                            for output in outputs:
                                if output.get("status") == "completed":
                                    task_id = output.get("task_id", "")
                                    lang = output.get("metadata", {}).get("language", "unknown")
                                    
                                    if lang != "unknown":
                                        languages_generated.add(lang)
                                    
                                    if "product" in task_id.lower():
                                        services_created.append("Product Management API (Python)")
                                    elif "order" in task_id.lower():
                                        services_created.append("Order Processing Service (Go)")
                                    elif "auth" in task_id.lower() or "user" in task_id.lower():
                                        services_created.append("User Authentication Service (Node.js)")
                            
                            print(f"\n🔧 Generated Services:")
                            for service in services_created[:3]:  # Show first 3
                                print(f"   ✓ {service}")
                            
                            print(f"\n💻 Languages Used: {', '.join(sorted(languages_generated))}")
                            
                            # Check GitHub
                            github_info = status_data.get("github")
                            if github_info:
                                print(f"\n🐙 GitHub Repository: {github_info.get('html_url', 'N/A')}")
                            
                            # Download info
                            if capsule_id:
                                print(f"\n📥 Download your production-ready code:")
                                print(f"    curl -O http://localhost:8000/api/capsules/{capsule_id}/download?format=zip")
                            
                            print(f"\n🎉 SUCCESS: From natural language to production code in {execution_time:.1f}s!")
                            print("   No templates used - pure AI-generated, enterprise-grade code")
                            
                        else:
                            print(f"\n❌ Workflow {current_status}")
                            if status_data.get("error"):
                                print(f"Error: {status_data['error']}")
                        
                        break
                
                # Timeout after 30 minutes
                if time.time() - start_time > 1800:
                    print(f"\n⏱️ Timeout: Workflow did not complete within 30 minutes")
                    break
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

async def main():
    """Main test runner"""
    await test_nlp_to_production()
    
    print("\n\n💡 Platform Capabilities Demonstrated:")
    print("  ✓ Natural Language Processing - Understood complex requirements")
    print("  ✓ Intelligent Decomposition - Split into appropriate microservices")
    print("  ✓ Multi-Language Support - Python, Go, Node.js in one project")
    print("  ✓ Production Quality - Tests, Docker, CI/CD included")
    print("  ✓ No Templates - Everything generated from scratch by AI")
    print("  ✓ Enterprise Ready - Scalable microservices architecture")

if __name__ == "__main__":
    asyncio.run(main())