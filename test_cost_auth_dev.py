#!/usr/bin/env python3
"""
Test cost tracking endpoints in development mode
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# In development mode, any token will work since CLERK_SECRET_KEY is not set properly
DEV_TOKEN = "development-token-12345"

def test_cost_with_dev_auth():
    """Test cost endpoints with development authentication"""
    print("🔐 Testing Cost Tracking with Development Auth")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
    
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
            print("✅ Cost estimation working!")
            estimates = estimate["data"]["model_estimates"]
            for model, info in estimates.items():
                print(f"   {model}: ${info['estimated_cost_usd']:.4f}")
    else:
        print(f"Error: {estimate_response.text}")
    
    # Test 2: Submit a workflow
    print("\n2️⃣ Submitting test workflow...")
    request_data = {
        "tenant_id": "dev-tenant",
        "user_id": "dev-user",
        "description": "Calculate factorial of a number"
    }
    
    exec_response = requests.post(f"{BASE_URL}/execute", json=request_data)
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
            # Wait for cost persistence
            time.sleep(2)
            
            # Test 3: Get Cost Report
            print("\n3️⃣ Getting Cost Report...")
            
            # Get costs for the last day
            cost_response = requests.get(
                f"{BASE_URL}/api/v2/costs",
                params={"period_days": 1},
                headers=headers
            )
            
            print(f"Status: {cost_response.status_code}")
            if cost_response.status_code == 200:
                cost_data = cost_response.json()
                if cost_data.get("success"):
                    print("✅ Cost report retrieved!")
                    report = cost_data.get("data", {})
                    print(f"\n📊 Cost Summary:")
                    print(f"   Total requests: {report.get('total_requests', 0)}")
                    print(f"   Total input tokens: {report.get('total_input_tokens', 0):,}")
                    print(f"   Total output tokens: {report.get('total_output_tokens', 0):,}")
                    print(f"   Total tokens: {report.get('total_tokens', 0):,}")
                    print(f"   💵 Total cost: ${report.get('total_cost_usd', 0):.6f}")
                    
                    # Show model breakdown
                    model_breakdown = report.get('model_breakdown', {})
                    if model_breakdown:
                        print("\n📈 Model Usage Breakdown:")
                        for model_key, usage in model_breakdown.items():
                            print(f"   {model_key}:")
                            print(f"     - Requests: {usage.get('count', 0)}")
                            print(f"     - Input tokens: {usage.get('input_tokens', 0):,}")
                            print(f"     - Output tokens: {usage.get('output_tokens', 0):,}")
                            print(f"     - Cost: ${usage.get('cost_usd', 0):.6f}")
            else:
                print(f"Error: {cost_response.text}")
            
            # Test 4: Get costs for specific workflow
            print(f"\n4️⃣ Getting costs for workflow {workflow_id}...")
            workflow_cost_response = requests.get(
                f"{BASE_URL}/api/v2/costs",
                params={"workflow_id": workflow_id},
                headers=headers
            )
            
            print(f"Status: {workflow_cost_response.status_code}")
            if workflow_cost_response.status_code == 200:
                workflow_cost_data = workflow_cost_response.json()
                if workflow_cost_data.get("success"):
                    print("✅ Workflow costs retrieved!")
                    # Note: The workflow ID might be stripped of prefix in the database
                    # so we might need to check without the "qlp-execution-" prefix
            
    # Test 5: Get metrics
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
            print(f"   Estimated cost: ${costs.get('estimated_cost', 0):.2f}")
    elif metrics_response.status_code == 403:
        print("❌ Metrics endpoint requires 'metrics:read' permission")
    
    print("\n" + "=" * 60)
    print("✅ Development Authentication Test Complete!")
    print("\n💡 Note: In development mode, authentication is mocked.")
    print("   The dev user has organization_id='org_dev_456'")
    print("   which is used as tenant_id for cost tracking.")

def test_direct_database():
    """Show how to check costs directly in database"""
    print("\n📊 Direct Database Queries:")
    print("-" * 60)
    print("""
# Get all costs for today:
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
    SELECT provider, model, COUNT(*) as requests, 
           SUM(input_tokens) as input, SUM(output_tokens) as output,
           SUM(total_cost_usd) as cost
    FROM llm_usage 
    WHERE created_at >= CURRENT_DATE
    GROUP BY provider, model
    ORDER BY cost DESC;"

# Get costs by tenant:
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
    SELECT tenant_id, COUNT(*) as requests, SUM(total_cost_usd) as cost
    FROM llm_usage 
    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY tenant_id
    ORDER BY cost DESC;"

# Get costs by workflow:
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
    SELECT workflow_id, COUNT(*) as requests, SUM(total_cost_usd) as cost
    FROM llm_usage 
    WHERE created_at >= CURRENT_DATE
    GROUP BY workflow_id
    ORDER BY cost DESC
    LIMIT 10;"
    """)

if __name__ == "__main__":
    test_cost_with_dev_auth()
    test_direct_database()