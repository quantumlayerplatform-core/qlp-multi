# QLP Python Client

Official Python client library for the Quantum Layer Platform v2 API.

## Installation

```bash
pip install qlp-client
```

## Quick Start

```python
from qlp_client import QLPClient

# Initialize client
client = QLPClient(api_key="your-api-key")

# Generate code
result = client.generate_and_wait(
    "Create a REST API for user management with authentication"
)

# Access generated code
print(result.source_code)
```

## Async Usage

```python
import asyncio
from qlp_client import QLPClient

async def main():
    async with QLPClient(api_key="your-api-key") as client:
        # Start generation
        workflow = await client.generate(
            "Create a Python web scraper",
            mode="complete"
        )
        
        # Wait for completion
        result = await client.wait_for_completion(workflow.workflow_id)
        
        # Download as zip
        zip_content = await client.download_capsule(
            result.capsule_id,
            format="zip"
        )

asyncio.run(main())
```

## Examples

### Basic Code Generation

```python
# Quick prototype
result = client.generate_basic("Create a fibonacci function")
```

### Production-Grade Application

```python
# Full production setup
result = client.generate_robust(
    "Create an e-commerce platform with microservices architecture",
    constraints={
        "language": "python",
        "framework": "fastapi",
        "database": "postgresql"
    }
)
```

### GitHub Integration

```python
# Generate and push to GitHub
result = client.generate_with_github(
    "Create a machine learning pipeline",
    github_token="ghp_...",
    repo_name="ml-pipeline",
    private=True
)

print(f"Repository created: {result.metadata['github_url']}")
```

### Custom Options

```python
# Full control over generation
result = client.generate_and_wait(
    "Create a data processing service",
    mode="complete",
    tier_override="T2",  # Use GPT-4 tier
    validation={
        "strict": True,
        "security": True,
        "performance": True
    },
    delivery={
        "format": "tar",
        "method": "download"
    }
)
```

## API Reference

### Client Initialization

```python
client = QLPClient(
    api_key="your-api-key",           # Required for authentication
    base_url="https://api.qlp.com",  # API endpoint (default: production)
    timeout=300.0                     # Request timeout in seconds
)
```

### Methods

#### `generate(description, **options)`
Start a code generation workflow.

**Parameters:**
- `description` (str): Natural language description
- `mode` (str): "basic", "complete", or "robust"
- `tier_override` (str): Force specific agent tier (T0-T3)
- `github` (dict): GitHub integration options
- `constraints` (dict): Language/framework constraints
- `requirements` (str): Additional requirements

**Returns:** `WorkflowResult` with workflow ID and status links

#### `get_status(workflow_id)`
Get current workflow status.

**Returns:** `WorkflowStatus` with progress information

#### `get_result(workflow_id)`
Get workflow result (completed workflows only).

**Returns:** `CapsuleResult` with generated code

#### `wait_for_completion(workflow_id, poll_interval=2.0, timeout=None)`
Wait for workflow to complete.

**Returns:** `CapsuleResult` when complete

#### `generate_and_wait(description, **options)`
Convenience method that combines generate() and wait_for_completion().

**Returns:** `CapsuleResult` with generated code

## Error Handling

```python
from qlp_client import QLPClient
import httpx

client = QLPClient(api_key="your-api-key")

try:
    result = client.generate_and_wait("Create something")
except httpx.HTTPStatusError as e:
    print(f"API error: {e.response.status_code}")
    print(f"Details: {e.response.text}")
except TimeoutError:
    print("Generation timed out")
except RuntimeError as e:
    print(f"Workflow failed: {e}")
```

## Rate Limiting

The API has rate limits. The client will automatically handle rate limit responses with exponential backoff.

## Support

- Documentation: https://docs.quantumlayerplatform.com
- API Reference: https://api.quantumlayerplatform.com/docs
- Issues: https://github.com/quantumlayer/qlp-python-client/issues

## License

MIT License - see LICENSE file for details.