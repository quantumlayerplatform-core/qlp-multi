#!/usr/bin/env python3
"""
Test script to verify validation is enabled in production
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


def format_workflow_status(status: Dict[str, Any]) -> str:
    """Format workflow status for display"""
    workflow_id = status.get('workflow_id', 'Unknown')
    state = status.get('status', 'Unknown')
    
    result = f"\n{'='*60}\n"
    result += f"Workflow ID: {workflow_id}\n"
    result += f"Status: {state}\n"
    
    if status.get('result'):
        result += f"\nResult Summary:\n"
        result += f"  Capsule ID: {status['result'].get('capsule_id', 'N/A')}\n"
        result += f"  Success: {status['result'].get('success', False)}\n"
        
        if status['result'].get('validation_passed') is not None:
            result += f"  Validation Passed: {status['result'].get('validation_passed')}\n"
        
        if status['result'].get('activities_completed'):
            result += f"\nActivities Completed ({len(status['result']['activities_completed'])}):\n"
            for activity in status['result']['activities_completed']:
                result += f"    - {activity}\n"
    
    result += f"{'='*60}\n"
    return result


async def test_validation():
    """Test validation in production"""
    
    # Production URL via LoadBalancer
    base_url = "http://85.210.81.162"
    
    # Simple request to trigger validation
    request_data = {
        "description": "Create a simple Python function that validates if a number is prime",
        "tenant_id": "test-tenant",
        "user_id": "test-user"
    }
    
    print("\n🚀 Testing Validation in Production")
    print(f"URL: {base_url}")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        try:
            # Submit request
            print("\n📤 Submitting request...")
            response = await client.post(
                f"{base_url}/execute",
                json=request_data
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to submit request: {response.status_code}")
                print(f"Response: {response.text}")
                return
            
            result = response.json()
            workflow_id = result.get('workflow_id')
            print(f"✅ Request submitted successfully")
            print(f"Workflow ID: {workflow_id}")
            
            # Poll for status
            print("\n⏳ Monitoring workflow progress...")
            max_attempts = 30  # 5 minutes max
            for i in range(max_attempts):
                status_response = await client.get(
                    f"{base_url}/status/{workflow_id}"
                )
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    
                    # Check for validation activity
                    if status.get('result') and status['result'].get('activities_completed'):
                        activities = status['result']['activities_completed']
                        validation_activities = [a for a in activities if 'validat' in a.lower()]
                        if validation_activities:
                            print(f"\n✅ Validation activities found: {validation_activities}")
                    
                    if status.get('status') in ['completed', 'failed']:
                        print(format_workflow_status(status))
                        
                        # Check validation results
                        if status.get('result'):
                            if status['result'].get('validation_passed') is not None:
                                if status['result']['validation_passed']:
                                    print("✅ VALIDATION ENABLED AND PASSED!")
                                else:
                                    print("⚠️  Validation enabled but failed")
                            else:
                                print("❌ Validation results not found in response")
                        break
                    else:
                        print(f"\r⏳ Status: {status.get('status', 'checking')}...", end='', flush=True)
                
                await asyncio.sleep(10)
            else:
                print("\n⏱️  Workflow did not complete within 5 minutes")
                
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_validation())