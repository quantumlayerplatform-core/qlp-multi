#!/usr/bin/env python3
"""
Test cost tracking endpoints with authentication
"""

import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Option 1: Using a Bearer token from Clerk
# You need to get this from your Clerk dashboard or by logging in
BEARER_TOKEN = os.getenv("CLERK_BEARER_TOKEN", "")

# Option 2: For development, you can use a mock token
# Check if development mode is enabled
DEVELOPMENT_MODE = True

def get_auth_headers():
    """Get authentication headers"""
    if BEARER_TOKEN:
        return {"Authorization": f"Bearer {BEARER_TOKEN}"}
    elif DEVELOPMENT_MODE:
        # In development, the auth might be mocked
        # Check src/common/clerk_auth.py for development mode behavior
        return {"Authorization": "Bearer development-token"}
    else:
        print("❌ No authentication token available")
        print("\nTo get a real token:")
        print("1. Go to your Clerk dashboard: https://dashboard.clerk.com")
        print("2. Find your application")
        print("3. Go to Users section and create a test user")
        print("4. Use the Clerk SDK to get a session token")
        print("\nOr for testing:")
        print("1. Set DEVELOPMENT_MODE=True in this script")
        print("2. Or set CLERK_BEARER_TOKEN environment variable")
        return None

def test_cost_endpoints():
    """Test cost tracking endpoints with authentication"""
    print("🔐 Testing Cost Tracking with Authentication")
    print("=" * 60)
    
    headers = get_auth_headers()
    if not headers:
        return
    
    # Test 1: Cost Estimation (no auth required for this one)
    print("\n1️⃣ Testing Cost Estimation...")
    estimate_response = requests.get(
        f"{BASE_URL}/api/v2/costs/estimate",
        params={
            "complexity": "medium",
            "tech_stack": ["Python", "FastAPI", "PostgreSQL"]
        },
        headers=headers
    )
    
    print(f"Response Status: {estimate_response.status_code}")
    if estimate_response.status_code == 200:
        estimate = estimate_response.json()
        if estimate.get("success"):
            print("✅ Cost estimation working with auth!")
            estimates = estimate["data"]["model_estimates"]
            for model, info in estimates.items():
                print(f"   {model}: ${info['estimated_cost_usd']:.4f} ({info['estimated_tokens']:,} tokens)")
    else:
        print(f"Response: {estimate_response.text}")
    
    # Test 2: Get Cost Report
    print("\n2️⃣ Testing Cost Report...")
    
    # First, let's execute something to generate costs
    print("   Executing a workflow to generate costs...")
    request_data = {
        "tenant_id": "test-tenant-auth",
        "user_id": "test-user-123",
        "description": "Test function for auth cost tracking"
    }
    
    exec_response = requests.post(f"{BASE_URL}/execute", json=request_data)
    if exec_response.status_code == 200:
        workflow_id = exec_response.json()["workflow_id"]
        print(f"   Workflow submitted: {workflow_id}")
        
        # Wait for completion
        print("   Waiting for completion...")
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(f"{BASE_URL}/status/{workflow_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                if status["status"] in ["COMPLETED", "FAILED"]:
                    break
        
        # Wait for cost data to persist
        time.sleep(2)
        
        # Now get the cost report
        cost_response = requests.get(
            f"{BASE_URL}/api/v2/costs",
            params={"period_days": 1},
            headers=headers
        )
        
        print(f"\nCost Report Response Status: {cost_response.status_code}")
        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            if cost_data.get("success"):
                print("✅ Cost report retrieved successfully!")
                report = cost_data.get("data", {})
                print(f"   Total requests: {report.get('total_requests', 0)}")
                print(f"   Total tokens: {report.get('total_tokens', 0):,}")
                print(f"   Total cost: ${report.get('total_cost_usd', 0):.6f}")
                
                # Show model breakdown if available
                model_breakdown = report.get('model_breakdown', {})
                if model_breakdown:
                    print("\n   Model Usage:")
                    for model_key, usage in model_breakdown.items():
                        print(f"   - {model_key}: ${usage.get('cost_usd', 0):.6f}")
        else:
            print(f"Response: {cost_response.text}")
    
    # Test 3: Get metrics (requires metrics:read permission)
    print("\n3️⃣ Testing Metrics Endpoint...")
    metrics_response = requests.get(
        f"{BASE_URL}/api/v2/metrics",
        params={"period": "1h"},
        headers=headers
    )
    
    print(f"Metrics Response Status: {metrics_response.status_code}")
    if metrics_response.status_code == 200:
        metrics = metrics_response.json()
        if metrics.get("success"):
            print("✅ Metrics retrieved successfully!")
            costs = metrics.get("data", {}).get("costs", {})
            print(f"   Total LLM cost: ${costs.get('total_llm_cost_usd', 0):.2f}")
    else:
        print(f"Response: {metrics_response.text}")
    
    print("\n" + "=" * 60)
    print("📌 Authentication Test Summary:")
    print(f"   - Cost Estimation: {'✅' if estimate_response.status_code == 200 else '❌'}")
    print(f"   - Cost Report: {'✅' if cost_response.status_code == 200 else '❌'}")
    print(f"   - Metrics: {'✅' if metrics_response.status_code == 200 else '❌'}")
    
    print("\n💡 Tips for Production Authentication:")
    print("1. Use Clerk SDK to authenticate users")
    print("2. Get the session token from Clerk after login")
    print("3. Pass the token in Authorization header")
    print("4. Token format: 'Bearer <session_token>'")
    print("5. Ensure user has required permissions for endpoints")

def show_clerk_integration_example():
    """Show example of Clerk integration"""
    print("\n📚 Clerk Integration Example:")
    print("-" * 60)
    print("""
# Frontend (React example):
import { useAuth } from '@clerk/clerk-react';

function CostDashboard() {
    const { getToken } = useAuth();
    
    const fetchCosts = async () => {
        const token = await getToken();
        const response = await fetch('http://localhost:8000/api/v2/costs', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await response.json();
        console.log(data);
    };
}

# Backend testing with curl:
curl -H "Authorization: Bearer <your-clerk-token>" \\
     http://localhost:8000/api/v2/costs?period_days=7

# Python SDK example:
from clerk import Clerk

clerk = Clerk(api_key="sk_test_...")
session = clerk.sessions.get("sess_...")
token = session.last_active_token

response = requests.get(
    "http://localhost:8000/api/v2/costs",
    headers={"Authorization": f"Bearer {token}"}
)
    """)

if __name__ == "__main__":
    test_cost_endpoints()
    show_clerk_integration_example()