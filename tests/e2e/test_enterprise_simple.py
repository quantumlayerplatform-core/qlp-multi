#!/usr/bin/env python3
"""
Test enterprise workflow with simpler requirements to verify timeout fixes
"""

import requests
import json
import time
import sys

# API endpoints
EXECUTE_ENDPOINT = "http://localhost:8000/execute"
STATUS_ENDPOINT = "http://localhost:8000/workflow/status"

def test_enterprise_simple():
    """Test with a simpler enterprise request"""
    print("🔧 Testing Enterprise Workflow - Simplified")
    print("=" * 60)
    
    # Simpler enterprise request - single microservice
    request_data = {
        "description": """
        Create a production-ready REST API service for user management with:
        - User registration, login, profile management
        - JWT authentication with refresh tokens
        - Role-based access control (admin, user roles)
        - PostgreSQL database with proper migrations
        - Input validation and error handling
        - Unit tests with >80% coverage
        - API documentation (OpenAPI/Swagger)
        - Docker configuration for deployment
        - Security best practices including threat modeling
        """,
        "requirements": """
        - Production-ready code with proper error handling
        - Comprehensive test coverage (>80%)
        - Security-first design with threat modeling
        - Performance optimized for 1000+ concurrent users
        - Proper logging and monitoring setup
        """,
        "tier_override": "T2",  # Use T2 for faster processing
        "user_id": "test-user-simple",
        "tenant_id": "enterprise-test-simple"
    }
    
    print(f"📤 Submitting simplified enterprise request...")
    print(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Submit request
        response = requests.post(EXECUTE_ENDPOINT, json=request_data)
        
        if response.status_code != 200:
            print(f"\n❌ Failed to start workflow!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.json()}")
            return
        
        result = response.json()
        workflow_id = result["workflow_id"]
        print(f"\n✅ Workflow started successfully!")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Status: {result['status']}")
        
        # Monitor workflow
        print(f"\n📊 Monitoring workflow progress...")
        start_time = time.time()
        
        while True:
            # Check status
            status_response = requests.get(f"{STATUS_ENDPOINT}/{workflow_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                workflow_status = status_data.get("workflow_status", "UNKNOWN")
                
                elapsed = time.time() - start_time
                print(f"\r⏳ Status: {workflow_status} | Elapsed: {elapsed:.0f}s ({elapsed/60:.1f}m)", end="", flush=True)
                
                if workflow_status in ["COMPLETED", "FAILED", "TERMINATED"]:
                    print(f"\n\n{'✅' if workflow_status == 'COMPLETED' else '❌'} Workflow {workflow_status.lower()}")
                    
                    if workflow_status == "COMPLETED":
                        # Get capsule details
                        capsule_endpoint = f"http://localhost:8000/capsule/{workflow_id}"
                        capsule_response = requests.get(capsule_endpoint)
                        if capsule_response.status_code == 200:
                            capsule_data = capsule_response.json()
                            print(f"\n📦 Capsule Details:")
                            print(f"   Status: {capsule_data.get('status')}")
                            print(f"   Files generated: {len(capsule_data.get('files', []))}")
                            print(f"   Validations passed: {capsule_data.get('validation_passed', False)}")
                    break
            
            time.sleep(3)
            
            # Timeout after 10 minutes
            if elapsed > 600:
                print(f"\n\n⏱️ Workflow timed out after 10 minutes")
                break
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enterprise_simple()