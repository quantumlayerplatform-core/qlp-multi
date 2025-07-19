#!/usr/bin/env python3
"""
Test to compare regular vs enterprise capsule generation
"""

import asyncio
import json
import time
from typing import Dict, Any

import httpx


BASE_URL = "http://localhost:8000"
TEST_REQUEST = {
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "description": "Create a Python function to calculate factorial of a number with tests"
}


async def execute_regular_request() -> Dict[str, Any]:
    """Execute regular request (non-enterprise)"""
    print("\n=== EXECUTING REGULAR REQUEST ===")
    
    async with httpx.AsyncClient(timeout=300) as client:
        # Submit regular request
        response = await client.post(f"{BASE_URL}/execute", json=TEST_REQUEST)
        response.raise_for_status()
        result = response.json()
        workflow_id = result["workflow_id"]
        print(f"Regular workflow started: {workflow_id}")
        
        # Wait for completion
        return await wait_for_workflow(client, workflow_id, "regular")


async def execute_enterprise_request() -> Dict[str, Any]:
    """Execute enterprise request"""
    print("\n=== EXECUTING ENTERPRISE REQUEST ===")
    
    async with httpx.AsyncClient(timeout=300) as client:
        # Submit enterprise request
        response = await client.post(f"{BASE_URL}/execute/enterprise", json=TEST_REQUEST)
        response.raise_for_status()
        result = response.json()
        workflow_id = result["workflow_id"]
        print(f"Enterprise workflow started: {workflow_id}")
        print(f"Enterprise features: {json.dumps(result.get('features', {}), indent=2)}")
        
        # Wait for completion
        return await wait_for_workflow(client, workflow_id, "enterprise")


async def wait_for_workflow(client: httpx.AsyncClient, workflow_id: str, request_type: str) -> Dict[str, Any]:
    """Wait for workflow to complete and return capsule"""
    print(f"\nWaiting for {request_type} workflow to complete...")
    
    max_attempts = 60  # 5 minutes max
    for attempt in range(max_attempts):
        try:
            status_response = await client.get(f"{BASE_URL}/status/{workflow_id}")
            status_response.raise_for_status()
            status = status_response.json()
            
            print(f"Attempt {attempt + 1}: Status = {status['status']}")
            
            if status["status"] == "COMPLETED":
                # Get the capsule
                capsule_response = await client.get(f"{BASE_URL}/capsule/{workflow_id}")
                if capsule_response.status_code == 200:
                    return capsule_response.json()
                else:
                    print(f"Capsule not ready yet: {capsule_response.status_code}")
            
            elif status["status"] in ["FAILED", "TERMINATED", "TIMED_OUT"]:
                print(f"Workflow failed with status: {status['status']}")
                return {"error": f"Workflow failed: {status['status']}"}
                
        except Exception as e:
            print(f"Error checking status: {e}")
        
        await asyncio.sleep(5)
    
    return {"error": "Workflow timed out"}


def compare_capsules(regular_capsule: Dict[str, Any], enterprise_capsule: Dict[str, Any]):
    """Compare regular and enterprise capsules"""
    print("\n" + "="*80)
    print("CAPSULE COMPARISON")
    print("="*80)
    
    # Check if either failed
    if "error" in regular_capsule:
        print(f"❌ Regular capsule failed: {regular_capsule['error']}")
    if "error" in enterprise_capsule:
        print(f"❌ Enterprise capsule failed: {enterprise_capsule['error']}")
    
    if "error" in regular_capsule or "error" in enterprise_capsule:
        return
    
    # Compare source files
    print("\n📁 SOURCE CODE FILES:")
    regular_files = set(regular_capsule.get("source_code", {}).keys())
    enterprise_files = set(enterprise_capsule.get("source_code", {}).keys())
    
    print(f"\nRegular capsule files ({len(regular_files)}):")
    for f in sorted(regular_files):
        print(f"  - {f}")
    
    print(f"\nEnterprise capsule files ({len(enterprise_files)}):")
    for f in sorted(enterprise_files):
        print(f"  - {f}")
    
    # Check additional enterprise files
    enterprise_only = enterprise_files - regular_files
    if enterprise_only:
        print(f"\n🌟 Additional enterprise files ({len(enterprise_only)}):")
        for f in sorted(enterprise_only):
            print(f"  - {f}")
    
    # Compare test files
    print("\n🧪 TEST FILES:")
    regular_tests = set(regular_capsule.get("tests", {}).keys())
    enterprise_tests = set(enterprise_capsule.get("tests", {}).keys())
    
    print(f"Regular tests: {len(regular_tests)}")
    print(f"Enterprise tests: {len(enterprise_tests)}")
    
    # Check documentation
    print("\n📚 DOCUMENTATION:")
    regular_doc_len = len(regular_capsule.get("documentation", ""))
    enterprise_doc_len = len(enterprise_capsule.get("documentation", ""))
    
    print(f"Regular documentation: {regular_doc_len} characters")
    print(f"Enterprise documentation: {enterprise_doc_len} characters")
    
    if enterprise_doc_len > regular_doc_len:
        print(f"✅ Enterprise documentation is {enterprise_doc_len - regular_doc_len} characters longer")
    
    # Check deployment config
    print("\n🚀 DEPLOYMENT CONFIG:")
    regular_deploy = regular_capsule.get("deployment_config", {})
    enterprise_deploy = enterprise_capsule.get("deployment_config", {})
    
    print(f"Regular deployment keys: {list(regular_deploy.keys())}")
    print(f"Enterprise deployment keys: {list(enterprise_deploy.keys())}")
    
    # Check for specific enterprise features
    print("\n✨ ENTERPRISE FEATURES CHECK:")
    enterprise_features = {
        "README.md": "README.md" in enterprise_files,
        "Dockerfile": "Dockerfile" in enterprise_files or "dockerfile" in enterprise_files,
        "CI/CD": any(".github/workflows" in f or ".gitlab-ci" in f for f in enterprise_files),
        "Documentation": any("docs/" in f for f in enterprise_files),
        "Testing Config": any("pytest.ini" in f or "setup.cfg" in f for f in enterprise_files),
        "Linting": any(".pylintrc" in f or ".flake8" in f for f in enterprise_files),
        "Type Checking": any("mypy.ini" in f or "py.typed" in f for f in enterprise_files),
        "Security": any("SECURITY.md" in f for f in enterprise_files),
        "Contributing": any("CONTRIBUTING.md" in f for f in enterprise_files),
        "License": any("LICENSE" in f for f in enterprise_files)
    }
    
    for feature, present in enterprise_features.items():
        status = "✅" if present else "❌"
        print(f"  {status} {feature}")


async def main():
    """Main comparison test"""
    print("🔍 Capsule Generation Comparison Test")
    print("="*80)
    
    # Execute both requests
    regular_result = await execute_regular_request()
    enterprise_result = await execute_enterprise_request()
    
    # Compare results
    compare_capsules(regular_result, enterprise_result)
    
    print("\n✅ Comparison test completed!")


if __name__ == "__main__":
    asyncio.run(main())