#!/usr/bin/env python3
"""
Test cost tracking with your Clerk credentials
"""

import requests
import json
import os
import jwt
import time
from datetime import datetime, timedelta

# Your Clerk credentials
CLERK_PUBLISHABLE_KEY = "pk_test_a25vd24tcGlnZW9uLTg5LmNsZXJrLmFjY291bnRzLmRldiQ"
CLERK_SECRET_KEY = "sk_test_s8sHdFfUq3ZTHBaXHTdKXxZq6ssVmBdu5b1oYJCGf0"

# Extract domain from publishable key
# Format: pk_test_<base64-encoded-domain>
import base64
encoded_domain = CLERK_PUBLISHABLE_KEY.split('_')[2].rstrip('$')
# Note: The domain appears to be "knowing-pigeon-89"
CLERK_DOMAIN = "knowing-pigeon-89"
CLERK_JWKS_URL = f"https://{CLERK_DOMAIN}.clerk.accounts.dev/.well-known/jwks.json"

BASE_URL = "http://localhost:8000"

def create_dev_jwt_token():
    """
    Create a development JWT token that mimics Clerk's structure
    This is for testing only - in production, use real Clerk tokens
    """
    # Token payload that mimics Clerk's structure
    payload = {
        "sub": "user_test_123",  # user_id
        "email": "test@quantumlayerplatform.com",
        "org_id": "org_test_456",  # organization_id (used as tenant_id)
        "org_role": "admin",
        "org_permissions": ["costs:read", "metrics:read"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour expiry
        "azp": CLERK_PUBLISHABLE_KEY,
        "metadata": {
            "test_user": True
        }
    }
    
    # For development testing, we'll create a simple token
    # In production, this would be signed by Clerk
    token = jwt.encode(payload, "development-secret", algorithm="HS256")
    return token

def test_cost_endpoints_with_token(token):
    """Test all cost endpoints with the provided token"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔐 Testing Cost Endpoints with Clerk Token")
    print("=" * 60)
    
    # Test 1: Cost Estimation
    print("\n1️⃣ Testing Cost Estimation...")
    estimate_response = requests.get(
        f"{BASE_URL}/api/v2/costs/estimate",
        params={
            "complexity": "medium",
            "tech_stack": ["Python", "FastAPI", "PostgreSQL"]
        },
        headers=headers
    )
    
    print(f"Status: {estimate_response.status_code}")
    if estimate_response.status_code == 200:
        estimate = estimate_response.json()
        if estimate.get("success"):
            print("✅ Cost estimation successful!")
            estimates = estimate["data"]["model_estimates"]
            for model, info in estimates.items():
                print(f"   {model}: ${info['estimated_cost_usd']:.4f} ({info['estimated_tokens']:,} tokens)")
        else:
            print(f"Error in response: {estimate}")
    else:
        print(f"Error: {estimate_response.text}")
    
    # Test 2: Execute a workflow to generate costs
    print("\n2️⃣ Executing test workflow...")
    exec_data = {
        "tenant_id": "org_test_456",  # Use the org_id from token
        "user_id": "user_test_123",
        "description": "Generate a Python function to calculate prime numbers"
    }
    
    exec_response = requests.post(f"{BASE_URL}/execute", json=exec_data)
    if exec_response.status_code == 200:
        workflow_id = exec_response.json()["workflow_id"]
        print(f"✅ Workflow submitted: {workflow_id}")
        
        # Wait for completion
        print("   Waiting for completion...")
        completed = False
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(f"{BASE_URL}/status/{workflow_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                if status["status"] == "COMPLETED":
                    completed = True
                    print("   ✅ Workflow completed!")
                    break
                elif status["status"] == "FAILED":
                    print("   ❌ Workflow failed!")
                    break
        
        if completed:
            # Wait for cost data to persist
            time.sleep(3)
            
            # Test 3: Get Cost Report
            print("\n3️⃣ Getting Cost Report...")
            cost_response = requests.get(
                f"{BASE_URL}/api/v2/costs",
                params={"period_days": 1},
                headers=headers
            )
            
            print(f"Status: {cost_response.status_code}")
            if cost_response.status_code == 200:
                cost_data = cost_response.json()
                if cost_data.get("success") and cost_data.get("data"):
                    print("✅ Cost report retrieved!")
                    report = cost_data["data"]
                    print(f"\n📊 Cost Summary for tenant '{report.get('tenant_id', 'N/A')}':")
                    print(f"   Total requests: {report.get('total_requests', 0)}")
                    print(f"   Total input tokens: {report.get('total_input_tokens', 0):,}")
                    print(f"   Total output tokens: {report.get('total_output_tokens', 0):,}")
                    print(f"   💵 Total cost: ${report.get('total_cost_usd', 0):.6f}")
                    
                    # Show model breakdown
                    model_breakdown = report.get('model_breakdown', {})
                    if model_breakdown:
                        print("\n📈 Model Usage:")
                        for model_key, usage in model_breakdown.items():
                            print(f"   {model_key}:")
                            print(f"     - Requests: {usage.get('count', 0)}")
                            print(f"     - Cost: ${usage.get('cost_usd', 0):.6f}")
                else:
                    print("⚠️ No cost data found")
                    print(f"Response: {cost_data}")
            else:
                print(f"Error: {cost_response.text}")
            
            # Test 4: Get workflow-specific costs
            print(f"\n4️⃣ Getting costs for workflow {workflow_id}...")
            workflow_cost_response = requests.get(
                f"{BASE_URL}/api/v2/costs",
                params={"workflow_id": workflow_id},
                headers=headers
            )
            
            print(f"Status: {workflow_cost_response.status_code}")
            if workflow_cost_response.status_code == 200:
                wf_data = workflow_cost_response.json()
                if wf_data.get("success") and wf_data.get("data"):
                    wf_report = wf_data["data"]
                    print(f"✅ Workflow cost: ${wf_report.get('total_cost_usd', 0):.6f}")
                    print(f"   Total requests: {wf_report.get('total_requests', 0)}")
    
    # Test 5: Metrics endpoint
    print("\n5️⃣ Testing Metrics Endpoint...")
    metrics_response = requests.get(
        f"{BASE_URL}/api/v2/metrics",
        params={"period": "1h"},
        headers=headers
    )
    
    print(f"Status: {metrics_response.status_code}")
    if metrics_response.status_code == 200:
        metrics = metrics_response.json()
        if metrics.get("success"):
            print("✅ Metrics retrieved!")
            costs = metrics.get("data", {}).get("costs", {})
            print(f"   LLM tokens used: {costs.get('llm_tokens', 0):,}")
            print(f"   Estimated cost: ${costs.get('estimated_cost', 0):.2f}")
    elif metrics_response.status_code == 403:
        print("⚠️ User needs 'metrics:read' permission")

def show_clerk_dashboard_instructions():
    """Show how to get a real token from Clerk dashboard"""
    print("\n📚 How to Get a Real Clerk Token")
    print("=" * 60)
    print(f"""
1. Go to your Clerk Dashboard:
   https://dashboard.clerk.com/apps/{CLERK_DOMAIN}/instances/development

2. Navigate to Users section and create a test user

3. Set the user's public metadata:
   {{
     "organization_id": "org_test_456",
     "permissions": ["costs:read", "metrics:read"]
   }}

4. Use one of these methods to get a token:

   a) Impersonate User (Easiest):
      - Click on the user
      - Click "Impersonate user"
      - Open browser DevTools
      - Look for API calls with Authorization header
      - Copy the Bearer token

   b) Use Clerk's API:
      curl -X POST https://api.clerk.com/v1/sessions \\
        -H "Authorization: Bearer {CLERK_SECRET_KEY}" \\
        -H "Content-Type: application/json" \\
        -d '{{"user_id": "USER_ID"}}'

   c) Create a simple test page:
      - Create an HTML file with Clerk's JavaScript
      - Sign in as the test user
      - Call clerk.session.getToken()

5. Once you have a real token, run:
   python test_cost_with_clerk.py --token YOUR_REAL_TOKEN
""")

def update_env_file():
    """Update .env file with correct Clerk settings"""
    print("\n🔧 Updating Environment Configuration...")
    
    env_updates = {
        "CLERK_SECRET_KEY": CLERK_SECRET_KEY,
        "CLERK_PUBLISHABLE_KEY": CLERK_PUBLISHABLE_KEY,
        "CLERK_JWKS_URL": CLERK_JWKS_URL
    }
    
    print("Add these to your .env file:")
    for key, value in env_updates.items():
        print(f"{key}={value}")
    
    print(f"\nYour Clerk domain is: {CLERK_DOMAIN}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test cost tracking with Clerk auth")
    parser.add_argument("--token", help="Use a specific Clerk token")
    parser.add_argument("--dev", action="store_true", help="Use development token")
    args = parser.parse_args()
    
    print("🔐 Clerk Cost Tracking Test")
    print(f"Domain: {CLERK_DOMAIN}")
    print(f"JWKS URL: {CLERK_JWKS_URL}")
    
    if args.token:
        print("\nUsing provided token")
        test_cost_endpoints_with_token(args.token)
    elif args.dev:
        print("\n⚠️ Using development token (for testing only)")
        dev_token = create_dev_jwt_token()
        test_cost_endpoints_with_token(dev_token)
    else:
        show_clerk_dashboard_instructions()
        print("\n💡 To test with a dev token, run:")
        print("   python test_cost_with_clerk.py --dev")
        
    # Show how to verify in database
    print("\n🔍 Verify costs directly in database:")
    print("   ./verify_cost_data.sh")
    
    # Update env file instructions
    update_env_file()