# QLP Capsule Management API

This document describes the production API endpoints for managing QLCapsules, including creation, versioning, delivery, and export functionality.

## Base URL

```
http://localhost:8000  # Development
https://api.quantumlayer.platform  # Production
```

## Authentication

All endpoints require valid authentication tokens in the `Authorization` header:

```
Authorization: Bearer <your-api-token>
```

## Core Capsule Endpoints

### 1. Create Capsule

**POST** `/generate/robust-capsule`

Creates a new QLCapsule with iterative refinement for production quality.

**Request Body:**
```json
{
  "id": "req-123",
  "tenant_id": "tenant-456", 
  "user_id": "user-789",
  "description": "Create a FastAPI microservice for user management",
  "requirements": "Must include authentication, CRUD operations, and Docker deployment",
  "constraints": {
    "language": "python",
    "framework": "fastapi",
    "database": "postgresql"
  },
  "metadata": {
    "target_score": 0.9,
    "save_to_disk": false
  }
}
```

**Response:**
```json
{
  "capsule_id": "cap-abc123",
  "request_id": "req-123",
  "robust_generation": true,
  "refinement_iterations": 3,
  "validation": {
    "passed": true,
    "score": 0.92,
    "production_ready": true,
    "issues": [],
    "recommendations": ["Capsule meets quality targets"]
  },
  "files_generated": 12,
  "confidence_score": 0.92,
  "languages": ["python"],
  "preview": {
    "source_files": ["main.py", "models.py", "auth.py", "database.py", "Dockerfile"],
    "test_files": ["test_main.py", "test_auth.py"],
    "has_dockerfile": true,
    "has_ci_cd": true,
    "has_tests": true
  }
}
```

### 2. Get Capsule Details

**GET** `/capsule/{capsule_id}`

Retrieves detailed information about a specific capsule.

**Response:**
```json
{
  "id": "cap-abc123",
  "request_id": "req-123",
  "tenant_id": "tenant-456",
  "user_id": "user-789",
  "status": "stored",
  "file_count": 12,
  "total_size_bytes": 45600,
  "confidence_score": 0.92,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "metadata": {
    "languages": ["python"],
    "frameworks": ["fastapi"],
    "deployment_ready": true
  }
}
```

### 3. List User Capsules

**GET** `/capsules?tenant_id={tenant_id}&user_id={user_id}&limit=50`

Lists capsules for a specific user.

**Response:**
```json
{
  "capsules": [
    {
      "id": "cap-abc123",
      "request_id": "req-123", 
      "status": "stored",
      "file_count": 12,
      "confidence_score": 0.92,
      "created_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "languages": ["python"],
        "description": "FastAPI microservice for user management"
      }
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

## Delivery Endpoints

### 4. Deliver Capsule

**POST** `/capsule/{capsule_id}/deliver`

Delivers a capsule to multiple destinations (cloud storage, Git repositories, etc.).

**Request Body:**
```json
{
  "version_id": "ver-xyz789",
  "delivery_configs": [
    {
      "mode": "s3",
      "destination": "my-deployment-bucket",
      "credentials": {
        "access_key_id": "AKIA...",
        "secret_access_key": "..."
      },
      "options": {
        "region": "us-east-1",
        "prefix": "deployments",
        "format": "tar.gz"
      }
    },
    {
      "mode": "github", 
      "destination": "myorg/my-microservice",
      "credentials": {
        "token": "ghp_..."
      },
      "options": {
        "branch": "main",
        "create_pr": true,
        "private": false
      }
    }
  ]
}
```

**Response:**
```json
{
  "capsule_id": "cap-abc123",
  "timestamp": "2024-01-15T11:00:00Z",
  "summary": {
    "total_destinations": 2,
    "successful": 2,
    "failed": 0
  },
  "destinations": [
    {
      "mode": "s3",
      "destination": "my-deployment-bucket",
      "success": true,
      "url": "s3://my-deployment-bucket/deployments/cap-abc123_20240115_110000.tar.gz",
      "signed_url": "https://my-deployment-bucket.s3.amazonaws.com/...",
      "checksum": "sha256:abc123..."
    },
    {
      "mode": "github",
      "destination": "myorg/my-microservice", 
      "success": true,
      "url": "https://github.com/myorg/my-microservice",
      "metadata": {
        "branch": "main",
        "pr_url": "https://github.com/myorg/my-microservice/pull/1"
      }
    }
  ],
  "recommendations": []
}
```

### 5. Stream Capsule

**GET** `/capsule/{capsule_id}/stream?format=tar.gz&chunk_size=8192`

Streams a capsule as a downloadable archive.

**Response:** Binary stream with appropriate Content-Type headers.

### 6. Export Capsule

**GET** `/capsule/{capsule_id}/export/{format}`

Exports capsule in specific formats (zip, helm, terraform, docker).

**Supported Formats:**
- `zip` - Returns binary ZIP archive
- `helm` - Returns Helm chart configuration as JSON
- `terraform` - Returns Terraform configuration files as JSON

## Versioning Endpoints

### 7. Create Version

**POST** `/capsule/{capsule_id}/version`

Creates a new version of an existing capsule.

**Request Body:**
```json
{
  "author": "john.doe@company.com",
  "message": "Added authentication middleware and improved error handling",
  "parent_version": "ver-abc123",
  "changes": [
    {
      "path": "middleware/auth.py",
      "type": "added",
      "size": 1024
    },
    {
      "path": "main.py", 
      "type": "modified",
      "size": 2048
    }
  ],
  "metadata": {
    "branch": "feature/auth-middleware"
  }
}
```

**Response:**
```json
{
  "version_id": "ver-def456",
  "capsule_id": "cap-abc123",
  "version_number": 2,
  "parent_version": "ver-abc123",
  "author": "john.doe@company.com",
  "message": "Added authentication middleware and improved error handling",
  "timestamp": "2024-01-15T12:00:00Z",
  "changes_count": 2
}
```

### 8. Get Version History

**GET** `/capsule/{capsule_id}/history?branch=main&limit=50`

Retrieves version history for a capsule.

**Response:**
```json
{
  "capsule_id": "cap-abc123",
  "branch": "main",
  "total_versions": 3,
  "versions": [
    {
      "version_id": "ver-def456",
      "version_number": 2,
      "author": "john.doe@company.com",
      "message": "Added authentication middleware",
      "timestamp": "2024-01-15T12:00:00Z",
      "parent_version": "ver-abc123",
      "tags": ["v1.1.0"]
    },
    {
      "version_id": "ver-abc123",
      "version_number": 1,
      "author": "system",
      "message": "Initial version",
      "timestamp": "2024-01-15T10:30:00Z",
      "parent_version": null,
      "tags": ["v1.0.0", "initial"]
    }
  ]
}
```

### 9. Create Branch

**POST** `/capsule/{capsule_id}/branch`

Creates a new development branch for a capsule.

**Request Body:**
```json
{
  "branch_name": "feature/new-endpoints",
  "from_version": "ver-abc123",
  "author": "jane.smith@company.com"
}
```

### 10. Tag Version

**POST** `/capsule/{capsule_id}/tag?version_id=ver-abc123&tag=v1.0.0&author=system`

Tags a specific version for release management.

## Security Endpoints

### 11. Sign Capsule

**POST** `/capsule/{capsule_id}/sign?private_key=your-signing-key`

Creates a digital signature for capsule integrity verification.

**Response:**
```json
{
  "capsule_id": "cap-abc123",
  "signature": "sha256:abcdef123456...",
  "algorithm": "HMAC-SHA256",
  "timestamp": "2024-01-15T13:00:00Z"
}
```

## Batch Operations

### 12. Batch Export

**POST** `/capsule/batch/export`

Exports multiple capsules in batch.

**Request Body:**
```json
{
  "capsule_ids": ["cap-abc123", "cap-def456", "cap-ghi789"],
  "format": "zip"
}
```

**Response:**
```json
{
  "total": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "capsule_id": "cap-abc123",
      "status": "success",
      "size": 45600,
      "url": "/capsule/cap-abc123/download"
    }
  ]
}
```

## Provider Configuration

### 13. List Delivery Providers

**GET** `/delivery/providers`

Lists all available delivery providers and their configuration requirements.

**Response:**
```json
{
  "providers": [
    {
      "name": "s3",
      "description": "Amazon S3 storage",
      "required_credentials": ["access_key_id", "secret_access_key"],
      "options": ["region", "prefix", "format"]
    },
    {
      "name": "azure",
      "description": "Azure Blob Storage", 
      "required_credentials": ["connection_string"],
      "options": ["prefix", "format"]
    },
    {
      "name": "github",
      "description": "GitHub repository",
      "required_credentials": ["token"],
      "options": ["branch", "create_pr", "private"]
    }
  ]
}
```

## Error Responses

All endpoints return standardized error responses:

```json
{
  "detail": "Descriptive error message",
  "error_code": "CAPSULE_NOT_FOUND",
  "timestamp": "2024-01-15T14:00:00Z",
  "request_id": "req-error-123"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (capsule/version not found)
- `409` - Conflict (version already exists)
- `422` - Validation Error (invalid request format)
- `500` - Internal Server Error

## Rate Limits

- **Standard Operations**: 100 requests/minute per user
- **Heavy Operations** (generation, delivery): 10 requests/minute per user
- **Batch Operations**: 5 requests/minute per user

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642176000
```

## Webhooks

Configure webhooks to receive notifications about capsule events:

### Events
- `capsule.created` - New capsule generated
- `capsule.delivered` - Capsule delivered to destination
- `version.created` - New version created
- `delivery.failed` - Delivery attempt failed

### Webhook Payload Example
```json
{
  "event": "capsule.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "capsule_id": "cap-abc123",
    "request_id": "req-123",
    "tenant_id": "tenant-456",
    "user_id": "user-789"
  }
}
```