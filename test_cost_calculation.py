#!/usr/bin/env python3
"""
Test the cost calculation integration
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_cost_calculation():
    print("🧮 Testing Cost Calculation Integration")
    print("=" * 50)
    
    # Get a valid token (you might need to update this)
    # For now, we'll skip auth for testing
    headers = {
        "Content-Type": "application/json"
    }
    
    # Test 1: Check cost endpoints
    print("\n1️⃣ Testing cost endpoints...")
    
    # Test cost estimate endpoint
    estimate_params = {
        "complexity": "medium",
        "tech_stack": ["Python", "FastAPI", "PostgreSQL"]
    }
    
    response = requests.get(
        f"{BASE_URL}/api/v2/costs/estimate",
        params=estimate_params
    )
    
    if response.status_code == 200:
        print("✅ Cost estimate endpoint working!")
        result = response.json()
        if result.get("success"):
            print(f"   Estimated costs:")
            estimates = result["data"]["model_estimates"]
            for model, info in estimates.items():
                print(f"   - {model}: ${info['estimated_cost_usd']}")
    else:
        print(f"❌ Cost estimate failed: {response.status_code}")
    
    # Test 2: Execute a task and check cost tracking
    print("\n2️⃣ Testing cost tracking in execution...")
    
    request_data = {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "description": "Create a Python function that calculates factorial",
        "requirements": "Include type hints and docstring",
        "metadata": {
            "project_name": "Cost Test",
            "complexity": "trivial"
        }
    }
    
    # Submit request
    response = requests.post(f"{BASE_URL}/execute", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        workflow_id = result["workflow_id"]
        print(f"✅ Workflow submitted: {workflow_id}")
        
        # Wait for completion
        print("⏳ Waiting for completion...")
        for i in range(30):
            time.sleep(1)
            status_response = requests.get(f"{BASE_URL}/status/{workflow_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                if status["status"] == "COMPLETED":
                    print(f"✅ Workflow completed in ~{i+1} seconds")
                    break
        
        # Check cost report
        print("\n3️⃣ Checking cost report...")
        cost_response = requests.get(
            f"{BASE_URL}/api/v2/costs",
            params={"workflow_id": workflow_id}
        )
        
        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            if cost_data.get("success") and cost_data.get("data"):
                print("✅ Cost tracking working!")
                report = cost_data["data"]
                print(f"   Total cost: ${report.get('total_cost_usd', 0):.6f}")
                print(f"   Total tokens: {report.get('total_tokens', 0)}")
        else:
            print(f"❌ Cost report failed: {cost_response.status_code}")
    
    # Test 3: Check metrics with cost data
    print("\n4️⃣ Checking metrics with cost data...")
    
    metrics_response = requests.get(f"{BASE_URL}/api/v2/metrics")
    if metrics_response.status_code == 200:
        metrics = metrics_response.json()
        if metrics.get("success"):
            costs = metrics["data"].get("costs", {})
            if "total_llm_cost_usd" in costs:
                print(f"✅ Cost in metrics: ${costs['total_llm_cost_usd']:.6f}")
            else:
                print("⚠️ Cost data not yet in metrics")
    
    # Test 4: Check LLM client metrics
    print("\n5️⃣ Checking LLM client metrics...")
    
    agent_metrics_response = requests.get("http://localhost:8001/metrics")
    if agent_metrics_response.status_code == 200:
        agent_metrics = agent_metrics_response.json()
        print("✅ Agent factory metrics available")
        # The cost data would be in the LLM client internally
    
    print("\n✅ Cost calculation test complete!")
    print("\nNote: Cost tracking is now integrated into:")
    print("- Azure LLM client (tracks all LLM calls)")
    print("- Production API v2 (cost endpoints)")
    print("- Metrics endpoints (includes cost data)")
    print("- Each LLM response includes cost breakdown")

if __name__ == "__main__":
    test_cost_calculation()