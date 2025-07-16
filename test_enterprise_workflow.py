#!/usr/bin/env python3
"""
Test Enterprise Workflow with Enhanced Heartbeat Management
"""
import requests
import json
import time
from datetime import datetime

def test_enterprise_workflow():
    """Test with enterprise-grade request"""
    
    # Enterprise-grade request
    request_data = {
        "description": """Build an enterprise-grade financial data processing system with the following components:
        1. Real-time data ingestion from multiple sources (REST APIs, WebSockets, CSV)
        2. Data validation and transformation pipeline
        3. Time-series database for historical data storage
        4. Real-time analytics engine with aggregation capabilities
        5. RESTful API for data access with authentication
        6. React dashboard for visualization
        7. Monitoring and alerting system
        8. Comprehensive test suite with >80% coverage""",
        "requirements": """
        - High availability with 99.9% uptime
        - Process 100,000 transactions per second
        - Sub-second latency for real-time queries
        - GDPR compliant data handling
        - Multi-tenant architecture
        - Horizontal scalability
        - Comprehensive logging and monitoring
        """,
        "constraints": {
            "technology_stack": {
                "backend": "Python with FastAPI",
                "database": "TimescaleDB and Redis",
                "frontend": "React with TypeScript",
                "deployment": "Kubernetes",
                "monitoring": "Prometheus and Grafana"
            },
            "quality_requirements": {
                "test_coverage": 85,
                "code_quality": "production",
                "documentation": "comprehensive"
            }
        },
        "tenant_id": "enterprise-test",
        "user_id": "enterprise-user"
    }
    
    print("🏢 Testing Enterprise Workflow with Enhanced Heartbeat Management")
    print("=" * 70)
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Start workflow
    print("📤 Submitting enterprise request...")
    response = requests.post(
        "http://localhost:8000/execute",
        json=request_data,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start workflow: {response.status_code}")
        print(response.text)
        return None
    
    workflow_data = response.json()
    workflow_id = workflow_data.get("workflow_id")
    
    print(f"✅ Workflow started: {workflow_id}")
    print()
    
    # Monitor workflow with detailed progress
    start_time = time.time()
    max_duration = 1800  # 30 minutes for enterprise workflow
    last_status = None
    last_progress = None
    heartbeat_count = 0
    
    print("📊 Monitoring Progress:")
    print("-" * 50)
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_duration:
            print(f"\n⏱️  Timeout after {elapsed:.1f} seconds")
            break
        
        try:
            status_response = requests.get(
                f"http://localhost:8000/workflow/status/{workflow_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status", "unknown")
                tasks_completed = status_data.get("tasks_completed", 0)
                tasks_total = status_data.get("tasks_total", 0)
                
                # Track heartbeats
                if status == "running":
                    heartbeat_count += 1
                
                # Show progress updates
                if status != last_status or tasks_completed != last_progress:
                    progress_pct = (tasks_completed / tasks_total * 100) if tasks_total > 0 else 0
                    print(f"\r[{elapsed:6.1f}s] Status: {status:12} | Tasks: {tasks_completed:2}/{tasks_total:2} ({progress_pct:5.1f}%) | Heartbeats: {heartbeat_count:3}", end="", flush=True)
                    last_status = status
                    last_progress = tasks_completed
                
                if status in ["completed", "failed"]:
                    print()  # New line after progress
                    print("-" * 50)
                    print(f"\n{'✅' if status == 'completed' else '❌'} Workflow {status}")
                    print(f"⏱️  Total Duration: {elapsed:.1f} seconds")
                    print(f"💓 Total Heartbeats: {heartbeat_count}")
                    
                    if status == "completed":
                        print(f"📦 Capsule ID: {status_data.get('capsule_id')}")
                        print(f"✨ Tasks Completed: {tasks_completed}/{tasks_total}")
                        
                        # Show execution details
                        if "execution_details" in status_data:
                            details = status_data["execution_details"]
                            print("\n📋 Execution Details:")
                            print(f"   - Pattern Used: {details.get('pattern_used', 'N/A')}")
                            print(f"   - Agent Tiers: {details.get('agent_tiers_used', [])}")
                            print(f"   - Validation Score: {details.get('validation_score', 0):.2f}")
                    else:
                        # Show error details
                        errors = status_data.get("errors", [])
                        if errors:
                            print("\n❌ Errors:")
                            for error in errors[:3]:  # Show first 3 errors
                                print(f"   - {error}")
                    
                    return status_data
            
        except requests.exceptions.Timeout:
            print(f"\n⚠️  Status check timeout at {elapsed:.1f}s")
        except Exception as e:
            print(f"\n⚠️  Error checking status: {str(e)}")
        
        time.sleep(5)  # Check every 5 seconds
    
    return None

if __name__ == "__main__":
    print("🚀 Enterprise Workflow Test Suite")
    print("================================\n")
    
    result = test_enterprise_workflow()
    
    print("\n" + "=" * 70)
    if result and result.get("status") == "completed":
        print("✅ Enterprise test completed successfully!")
        print("🎉 Enhanced heartbeat management is working properly!")
    else:
        print("❌ Enterprise test failed")
        print("Please check logs for timeout issues")