# Dynamic API Configuration

This document explains how the API dynamically configures URLs and security headers based on the environment.

## Overview

The API now supports dynamic configuration of:
- Server URLs in OpenAPI documentation
- Content Security Policy (CSP) headers
- CORS allowed origins
- CDN URLs for documentation assets

## Configuration Methods

### 1. Environment Variables

The following environment variables control API behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment type: development, staging, or production |
| `API_BASE_URL` | None | Custom API URL that overrides all other URLs |
| `PRODUCTION_API_URL` | `https://api.quantumlayerplatform.com` | Production API URL |
| `STAGING_API_URL` | `https://staging-api.quantumlayerplatform.com` | Staging API URL |
| `LOCAL_API_URL` | `http://localhost:8000` | Local development URL |
| `AUTO_DETECT_HOST` | `true` | Auto-detect host from request in development |
| `ADDITIONAL_ALLOWED_ORIGINS` | Empty | Comma-separated list of additional allowed origins |
| `SWAGGER_CDN_URL` | `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0` | Swagger UI CDN |
| `REDOC_CDN_URL` | `https://cdn.jsdelivr.net/npm/redoc@2.0.0` | ReDoc CDN |

### 2. Auto-Detection

In development mode with `AUTO_DETECT_HOST=true`, the API will:
- Detect the current host and port from incoming requests
- Add the detected URL as the primary server in OpenAPI docs
- This allows the API to work correctly when accessed via different URLs (localhost, Docker, ngrok, etc.)

### 3. Environment-Based Behavior

#### Development (default)
- Auto-detects host from requests
- Allows localhost and 127.0.0.1 origins
- Shows all server options in docs

#### Staging
- Uses staging URL as primary
- Shows production URL as secondary option
- Stricter CSP headers

#### Production
- Uses production URL as primary
- Most restrictive security headers
- No auto-detection

## Usage Examples

### Local Development (Default)
```bash
# No configuration needed - auto-detection works out of the box
python main.py
```

### Custom Local Port
```bash
LOCAL_API_URL=http://localhost:3000 python main.py
```

### Production Deployment
```bash
ENVIRONMENT=production \
API_BASE_URL=https://api.yourdomain.com \
python main.py
```

### Docker Compose
```yaml
services:
  api:
    environment:
      - ENVIRONMENT=development
      - AUTO_DETECT_HOST=true
```

### Kubernetes
```yaml
env:
  - name: ENVIRONMENT
    value: "production"
  - name: API_BASE_URL
    value: "https://api.quantumlayerplatform.com"
  - name: AUTO_DETECT_HOST
    value: "false"
```

## Security Considerations

### Content Security Policy (CSP)

The API automatically generates CSP headers based on the environment:
- Allows required CDN origins for documentation assets
- Restricts connections to configured API URLs only
- Prevents XSS and data injection attacks

### CORS Configuration

Add allowed origins for cross-origin requests:
```bash
ADDITIONAL_ALLOWED_ORIGINS=https://app.example.com,https://dashboard.example.com
```

## Troubleshooting

### Documentation Not Loading

1. Check CSP headers in browser console
2. Ensure CDN URLs are accessible
3. Verify API_BASE_URL matches actual deployment

### Wrong Server URL in Docs

1. Set `API_BASE_URL` explicitly
2. Check `ENVIRONMENT` variable
3. Disable auto-detection in production: `AUTO_DETECT_HOST=false`

### CORS Issues

1. Add origin to `ADDITIONAL_ALLOWED_ORIGINS`
2. Check that the origin includes protocol (https://)
3. Restart the application after changes

## Migration Guide

### From Hardcoded URLs

1. Remove any hardcoded URLs from code
2. Set appropriate environment variables
3. Test in each environment

### Example Migration

Before:
```python
servers = [
    {"url": "https://api.quantumlayerplatform.com", "description": "Production"}
]
```

After:
```bash
# Set in .env or deployment config
ENVIRONMENT=production
PRODUCTION_API_URL=https://api.quantumlayerplatform.com
```

The application will now use the configuration dynamically!