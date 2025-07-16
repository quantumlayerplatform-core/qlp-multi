import requests
import json

# Test T1 agent with a medium complexity task
request_data = {
    "task": {
        "id": "test-task-002",
        "type": "code_generation",
        "description": "Create a REST API endpoint for user registration with validation",
        "complexity": "medium"
    },
    "tier": "T1",
    "context": {
        "framework": "FastAPI",
        "language": "python"
    }
}

response = requests.post(
    "http://localhost:8001/execute",
    json=request_data,
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response.status_code}")
result = response.json()
print(f"Status: {result.get('status')}")
print(f"Agent Tier: {result.get('agent_tier_used')}")
print(f"Output Type: {result.get('output_type')}")

# Check if output has 'code' field
output = result.get('output', {})
if isinstance(output, dict):
    has_code = 'code' in output
    print(f"Has 'code' field: {has_code}")
    if has_code:
        print(f"Code preview: {output['code'][:100]}...")
else:
    print(f"Output is not a dict: {type(output)}")

print("\nFull output structure:")
print(json.dumps(result, indent=2))
