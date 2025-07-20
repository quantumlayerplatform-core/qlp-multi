# API Migration Guide - v1 to v2

## Overview

The Quantum Layer Platform is consolidating its API endpoints from 56+ endpoints to a streamlined set of ~10 core endpoints. This guide helps you migrate from v1 endpoints to the new v2 unified API.

## Key Changes

### 1. Single Entry Point
All code generation workflows now use a single endpoint with options:
- **Old**: Multiple endpoints (`/execute`, `/generate/capsule`, `/generate/complete-with-github`, etc.)
- **New**: Single endpoint `/v2/execute` with `options` parameter

### 2. RESTful Design
Resources follow REST conventions:
- **Old**: `/workflow/status/{id}`, `/status/{id}` (duplicates)
- **New**: `/v2/workflows/{id}` (single status endpoint)

### 3. Consistent Response Format
All responses follow a unified structure with helpful links.

## Migration Mappings

### Code Generation Endpoints

#### Basic Execution
```python
# Old way
POST /execute
{
  "description": "Create a REST API",
  "user_id": "user123"
}

# New way
POST /v2/execute
{
  "description": "Create a REST API",
  "user_id": "user123",
  "options": {
    "mode": "complete"
  }
}
```

#### Basic Capsule Generation
```python
# Old way
POST /generate/capsule
{
  "description": "Create a function"
}

# New way
POST /v2/execute
{
  "description": "Create a function",
  "options": {
    "mode": "basic"
  }
}
```

#### GitHub Integration
```python
# Old way
POST /generate/complete-with-github
{
  "description": "Create API",
  "github_token": "token",
  "repo_name": "my-api"
}

# New way
POST /v2/execute
{
  "description": "Create API",
  "options": {
    "mode": "complete",
    "github": {
      "enabled": true,
      "token": "token",
      "repo_name": "my-api",
      "private": false
    }
  }
}
```

#### Robust/Production Generation
```python
# Old way
POST /generate/robust-capsule
{
  "description": "Production e-commerce platform"
}

# New way
POST /v2/execute
{
  "description": "Production e-commerce platform",
  "options": {
    "mode": "robust"
  }
}
```

### Status Checking

```python
# Old way
GET /workflow/status/{workflow_id}
GET /status/{workflow_id}  # duplicate

# New way
GET /v2/workflows/{workflow_id}
```

### Getting Results

```python
# Old way
GET /capsule/{capsule_id}

# New way
GET /v2/workflows/{workflow_id}/result
# Returns capsule with download links
```

## Options Reference

### Execution Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `basic` | Minimal validation, fast execution | Prototypes, simple scripts |
| `complete` | Standard validation and tests | Most use cases |
| `robust` | Full validation, production features | Enterprise applications |

### Option Parameters

```typescript
{
  "options": {
    // Execution mode
    "mode": "basic" | "complete" | "robust",
    
    // Agent tier override
    "tier_override": "T0" | "T1" | "T2" | "T3",
    
    // GitHub integration
    "github": {
      "enabled": boolean,
      "token": string,
      "repo_name": string,
      "private": boolean,
      "create_pr": boolean,
      "enterprise_structure": boolean
    },
    
    // Delivery options
    "delivery": {
      "format": "zip" | "tar" | "targz",
      "stream": boolean,
      "method": "download" | "email" | "s3"
    },
    
    // Validation options
    "validation": {
      "strict": boolean,
      "security": boolean,
      "performance": boolean
    },
    
    // Additional metadata
    "metadata": {
      // Custom key-value pairs
    }
  }
}
```

## Response Format

### Unified Execute Response
```json
{
  "workflow_id": "qlp-v2-complete-abc123",
  "request_id": "abc123",
  "status": "submitted",
  "message": "Workflow started in complete mode",
  "links": {
    "status": "http://api.qlp.com/v2/workflows/qlp-v2-complete-abc123",
    "cancel": "http://api.qlp.com/v2/workflows/qlp-v2-complete-abc123/cancel",
    "result": "http://api.qlp.com/v2/workflows/qlp-v2-complete-abc123/result"
  },
  "metadata": {
    "mode": "complete",
    "estimated_duration": "3-5 minutes",
    "features": ["standard_validation", "unit_tests"]
  }
}
```

### Status Response
```json
{
  "workflow_id": "qlp-v2-complete-abc123",
  "status": "RUNNING",
  "started_at": "2025-01-15T10:00:00Z",
  "completed_at": null,
  "execution_time": 45.2,
  "progress": {
    "percentage": 50,
    "current_step": "processing",
    "message": "Workflow in progress"
  }
}
```

## Deprecation Timeline

### Phase 1: Soft Deprecation (Now - March 2025)
- Old endpoints continue to work
- Deprecation warnings in responses
- Documentation updated to show v2 as primary

### Phase 2: Migration Period (March - June 2025)
- Old endpoints redirect to v2 internally
- Warning headers added to responses
- Email notifications to active users

### Phase 3: Sunset (July 2025)
- Old endpoints return 410 Gone
- Only v2 endpoints available

## Code Examples

### Python Migration

```python
# Old client code
import requests

# Multiple endpoints to remember
response = requests.post(
    "https://api.qlp.com/generate/complete-with-github",
    json={
        "description": "Create REST API",
        "github_token": token,
        "repo_name": "my-api"
    }
)

# New client code
response = requests.post(
    "https://api.qlp.com/v2/execute",
    json={
        "description": "Create REST API",
        "options": {
            "mode": "complete",
            "github": {
                "enabled": True,
                "token": token,
                "repo_name": "my-api"
            }
        }
    }
)

# Consistent status checking
workflow_id = response.json()["workflow_id"]
status = requests.get(f"https://api.qlp.com/v2/workflows/{workflow_id}")
```

### JavaScript/TypeScript Migration

```typescript
// Old way - multiple endpoints
const generateWithGitHub = async (description: string) => {
  const response = await fetch('/generate/complete-with-github', {
    method: 'POST',
    body: JSON.stringify({
      description,
      github_token: token,
      repo_name: 'my-api'
    })
  });
  return response.json();
};

// New way - single endpoint with options
const generate = async (description: string, options = {}) => {
  const response = await fetch('/v2/execute', {
    method: 'POST',
    body: JSON.stringify({
      description,
      options: {
        mode: 'complete',
        ...options
      }
    })
  });
  
  const result = await response.json();
  
  // Use provided links for status
  const status = await fetch(result.links.status);
  return status.json();
};
```

## Common Patterns

### 1. Simple Code Generation
```python
# Just generate code, no extras
response = requests.post("/v2/execute", json={
    "description": "Fibonacci function",
    "options": {"mode": "basic"}
})
```

### 2. Production Application
```python
# Full production setup with GitHub
response = requests.post("/v2/execute", json={
    "description": "E-commerce platform",
    "options": {
        "mode": "robust",
        "github": {
            "enabled": True,
            "token": github_token,
            "repo_name": "ecommerce-platform",
            "private": True,
            "enterprise_structure": True
        }
    }
})
```

### 3. Custom Constraints
```python
# Specific requirements
response = requests.post("/v2/execute", json={
    "description": "Data processing pipeline",
    "constraints": {
        "language": "python",
        "framework": "fastapi",
        "python_version": "3.11"
    },
    "options": {
        "mode": "complete",
        "tier_override": "T2"  # Use GPT-4 tier
    }
})
```

## FAQ

### Q: What happens to my existing integrations?
A: Old endpoints will continue working until July 2025, giving you time to migrate.

### Q: How do I know which mode to use?
A: 
- `basic`: Quick prototypes, simple scripts
- `complete`: Most production use cases (default)
- `robust`: Mission-critical applications

### Q: Can I still use specific agent tiers?
A: Yes, use `options.tier_override` to specify T0, T1, T2, or T3.

### Q: What about webhook callbacks?
A: Webhooks are being redesigned for v2. Use polling with the status link for now.

## Support

For migration assistance:
- Documentation: https://docs.qlp.com/api/v2
- Migration tool: https://migrate.qlp.com
- Support: support@quantumlayerplatform.com

## Automated Migration Tool

We provide a tool to automatically update your code:

```bash
# Install migration tool
npm install -g @qlp/migrate

# Analyze your codebase
qlp-migrate analyze ./src

# Apply migrations
qlp-migrate apply ./src --backup
```

The tool will:
1. Find all API calls to old endpoints
2. Convert them to v2 format
3. Create backups before changes
4. Generate a migration report