#!/usr/bin/env python3
"""
Test the /execute endpoint with cost tracking
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_execute_with_cost():
    print("💰 Testing /execute Endpoint with Cost Tracking")
    print("=" * 50)
    
    # Test request
    request_data = {
        "tenant_id": "demo-tenant",
        "user_id": "demo-user",
        "description": "Create a Python FastAPI endpoint that returns the current time in JSON format with timezone support",
        "requirements": "Include proper error handling, type hints, and OpenAPI documentation",
        "metadata": {
            "project_name": "Time API with Cost Tracking",
            "complexity": "simple"
        }
    }
    
    print("\n📝 Request Details:")
    print(f"Description: {request_data['description']}")
    print(f"Complexity: {request_data['metadata']['complexity']}")
    
    # Submit execution request
    print("\n🚀 Submitting execution request...")
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/execute", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        workflow_id = result["workflow_id"]
        request_id = result.get("request_id", workflow_id)  # Use workflow_id if request_id not present
        
        print(f"✅ Workflow submitted successfully!")
        print(f"   Workflow ID: {workflow_id}")
        if "request_id" in result:
            print(f"   Request ID: {request_id}")
        print(f"   Status: {result['status']}")
        
        # Poll for completion
        print("\n⏳ Waiting for completion...")
        completed = False
        for i in range(60):  # Wait up to 60 seconds
            time.sleep(2)
            
            # Check status
            status_response = requests.get(f"{BASE_URL}/status/{workflow_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                current_status = status["status"]
                
                if current_status == "COMPLETED":
                    completed = True
                    execution_time = time.time() - start_time
                    print(f"\n✅ Workflow completed in {execution_time:.1f} seconds!")
                    print(f"   Start time: {status['start_time']}")
                    print(f"   End time: {status['close_time']}")
                    break
                elif current_status == "FAILED":
                    print(f"\n❌ Workflow failed!")
                    break
                else:
                    print(f"\r⏳ Status: {current_status} ({i*2}s)...", end="", flush=True)
        
        if completed:
            # Get the capsule
            print("\n📦 Retrieving generated capsule...")
            execution_id = workflow_id.replace("qlp-execution-", "")
            capsule_response = requests.get(f"{BASE_URL}/capsule/{execution_id}")
            
            if capsule_response.status_code == 200:
                capsule_data = capsule_response.json()
                print("✅ Capsule retrieved successfully!")
                
                # Show generated code preview
                if "source_code" in capsule_data:
                    for file_name, content in list(capsule_data["source_code"].items())[:1]:
                        print(f"\n📄 Generated file: {file_name}")
                        print("-" * 50)
                        print(content[:500] + "..." if len(content) > 500 else content)
                        print("-" * 50)
            
            # Now check the cost report
            print("\n💰 Checking Cost Report...")
            
            # Method 1: Get cost for this specific workflow
            cost_response = requests.get(
                f"{BASE_URL}/api/v2/costs",
                params={"workflow_id": workflow_id}
            )
            
            if cost_response.status_code == 200:
                cost_data = cost_response.json()
                if cost_data.get("success") and cost_data.get("data"):
                    report = cost_data["data"]
                    
                    print("\n📊 Cost Breakdown:")
                    print(f"   Workflow ID: {report.get('workflow_id', workflow_id)}")
                    print(f"   Total Requests: {report.get('total_requests', 0)}")
                    print(f"   Total Input Tokens: {report.get('total_input_tokens', 0):,}")
                    print(f"   Total Output Tokens: {report.get('total_output_tokens', 0):,}")
                    print(f"   Total Tokens: {report.get('total_tokens', 0):,}")
                    print(f"   💵 Total Cost: ${report.get('total_cost_usd', 0):.6f}")
                    
                    # Show model breakdown if available
                    model_breakdown = report.get('model_breakdown', {})
                    if model_breakdown:
                        print("\n   Model Usage:")
                        for model, usage in model_breakdown.items():
                            print(f"   - {model}:")
                            print(f"     Requests: {usage.get('count', 0)}")
                            print(f"     Tokens: {usage.get('input_tokens', 0) + usage.get('output_tokens', 0):,}")
                            print(f"     Cost: ${usage.get('cost_usd', 0):.6f}")
                    
                    if report.get('average_cost_per_request'):
                        print(f"\n   Average Cost per Request: ${report['average_cost_per_request']:.6f}")
            else:
                print(f"❌ Failed to get cost report: {cost_response.status_code}")
                if cost_response.status_code == 401:
                    print("   Note: Cost endpoints require authentication")
            
            # Method 2: Check platform metrics
            print("\n📈 Checking Platform Metrics...")
            metrics_response = requests.get(f"{BASE_URL}/api/v2/metrics")
            
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                if metrics.get("success") and metrics.get("data"):
                    costs = metrics["data"].get("costs", {})
                    print(f"   Total Platform LLM Cost: ${costs.get('total_llm_cost_usd', 0):.6f}")
            
            # Method 3: Get cost estimate for comparison
            print("\n🔮 Cost Estimate (for comparison):")
            estimate_response = requests.get(
                f"{BASE_URL}/api/v2/costs/estimate",
                params={
                    "complexity": request_data["metadata"]["complexity"],
                    "tech_stack": ["Python", "FastAPI"]
                }
            )
            
            if estimate_response.status_code == 200:
                estimate_data = estimate_response.json()
                if estimate_data.get("success"):
                    estimates = estimate_data["data"]["model_estimates"]
                    for model, info in estimates.items():
                        print(f"   {model}: ${info['estimated_cost_usd']:.4f} ({info['estimated_tokens']:,} tokens)")
        
        else:
            print(f"\n⚠️ Workflow still running after 120 seconds")
            
    else:
        print(f"\n❌ Request failed: {response.status_code}")
        print(response.text)
    
    print("\n✅ Test complete!")
    print("\nCost Tracking Summary:")
    print("- Every LLM call is automatically tracked")
    print("- Costs are calculated based on actual token usage")
    print("- Results are available via /api/v2/costs endpoint")
    print("- Costs are linked to workflow, tenant, and user")

if __name__ == "__main__":
    test_execute_with_cost()