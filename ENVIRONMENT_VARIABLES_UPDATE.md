# Environment Variables Update Guide

## Overview
This guide lists all environment variables that need to be updated when changing from `quantumlayer.com` to `quantumlayerplatform.com`.

## Production Environment Variables

### API URLs
```bash
# Old
PRODUCTION_API_URL=https://api.quantumlayer.com
STAGING_API_URL=https://staging-api.quantumlayer.com
API_BASE_URL=https://api.quantumlayer.com

# New
PRODUCTION_API_URL=https://api.quantumlayerplatform.com
STAGING_API_URL=https://staging-api.quantumlayerplatform.com
API_BASE_URL=https://api.quantumlayerplatform.com
```

### Security & CORS
```bash
# Old
ALLOWED_HOSTS=*.quantumlayer.com,api.quantumlayer.com
CORS_ORIGINS=https://app.quantumlayer.com,https://dashboard.quantumlayer.com
TRUSTED_HOSTS=*.quantumlayer.com,localhost

# New
ALLOWED_HOSTS=*.quantumlayerplatform.com,api.quantumlayerplatform.com
CORS_ORIGINS=https://app.quantumlayerplatform.com,https://dashboard.quantumlayerplatform.com
TRUSTED_HOSTS=*.quantumlayerplatform.com,localhost
```

### Email Configuration
```bash
# Old
FROM_EMAIL=noreply@quantumlayer.com

# New
FROM_EMAIL=noreply@quantumlayerplatform.com
```

## Client Configuration

### Python Client
The default base URL in `client/python/qlp_client.py`:
```python
# Old
base_url: str = "https://api.quantumlayer.com"

# New
base_url: str = "https://api.quantumlayerplatform.com"
```

### JavaScript/TypeScript Client
The default base URL in `client/javascript/src/index.ts`:
```typescript
// Old
baseUrl = 'https://api.quantumlayer.com'

// New
baseUrl = 'https://api.quantumlayerplatform.com'
```

## External Services Update Checklist

### 1. DNS Records
- [ ] Update A records for api.quantumlayerplatform.com
- [ ] Update A records for staging-api.quantumlayerplatform.com
- [ ] Update A records for app.quantumlayerplatform.com
- [ ] Update A records for dashboard.quantumlayerplatform.com
- [ ] Update A records for docs.quantumlayerplatform.com
- [ ] Update A records for status.quantumlayerplatform.com
- [ ] Update MX records for email (@quantumlayerplatform.com)

### 2. SSL Certificates
- [ ] Obtain SSL certificate for *.quantumlayerplatform.com
- [ ] Obtain SSL certificate for api.quantumlayerplatform.com
- [ ] Configure certificates in load balancer/ingress

### 3. OAuth & Authentication (Clerk)
- [ ] Update allowed redirect URLs
- [ ] Update webhook endpoints
- [ ] Update email sender domain

### 4. Third-Party Integrations
- [ ] Update GitHub webhook URLs
- [ ] Update monitoring service endpoints
- [ ] Update email service sender domain
- [ ] Update any API documentation references

### 5. Container Registry & Deployment
- [ ] Update any hardcoded domains in Kubernetes manifests
- [ ] Update ingress rules
- [ ] Update service mesh configurations

## Testing Checklist

After updating the domain:

1. **API Endpoints**
   - [ ] Test production API at https://api.quantumlayerplatform.com
   - [ ] Test staging API at https://staging-api.quantumlayerplatform.com
   - [ ] Verify OpenAPI documentation loads correctly

2. **Authentication**
   - [ ] Test login flow
   - [ ] Verify JWT tokens are issued correctly
   - [ ] Test organization/tenant isolation

3. **CORS**
   - [ ] Test requests from app.quantumlayerplatform.com
   - [ ] Test requests from dashboard.quantumlayerplatform.com
   - [ ] Verify preflight requests work correctly

4. **Email**
   - [ ] Test email sending from noreply@quantumlayerplatform.com
   - [ ] Verify email templates use correct domain

5. **Client Libraries**
   - [ ] Test Python client with new domain
   - [ ] Test JavaScript client with new domain
   - [ ] Verify environment variable overrides work

## Rollback Plan

If issues arise after the domain update:

1. Restore files from backup:
   ```bash
   cp domain_update_backup_*/\*.bak .
   ```

2. Revert environment variables to original values

3. Update DNS records back to quantumlayer.com

4. Restart all services

## Notes

- The domain change affects both code and infrastructure
- Ensure all team members are aware of the change
- Update any documentation or training materials
- Consider setting up redirects from old domain to new domain during transition