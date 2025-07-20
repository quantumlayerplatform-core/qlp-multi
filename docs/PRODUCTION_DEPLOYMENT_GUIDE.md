# Production Deployment Guide

This guide covers deploying the Quantum Layer Platform with production-grade API v2.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Vercel      │────▶│    Railway     │────▶│  Azure OpenAI   │
│   (Frontend)    │     │   (Backend)    │     │     (LLMs)      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        │
┌─────────────────┐     ┌─────────────────┐              │
│                 │     │                 │              │
│     Clerk       │     │  PostgreSQL    │              │
│    (Auth)       │     │   + Redis      │              │
│                 │     │                 │              │
└─────────────────┘     └─────────────────┘              │
                                │                         │
                                ▼                         │
                        ┌─────────────────┐              │
                        │                 │              │
                        │    Temporal     │◀─────────────┘
                        │  (Workflows)    │
                        │                 │
                        └─────────────────┘
```

## Prerequisites

1. **Accounts Required**:
   - Railway account
   - Vercel account
   - Clerk account
   - Azure account (for Azure OpenAI)
   - GitHub account
   - Sentry account (monitoring)

2. **API Keys Needed**:
   - Clerk Secret Key
   - Azure OpenAI API Key
   - OpenAI API Key (fallback)
   - Anthropic API Key (optional)
   - GitHub Personal Access Token
   - Sentry DSN

## Step 1: Configure Clerk Authentication

### 1.1 Create Clerk Application
```bash
# Go to https://dashboard.clerk.com
# Create new application
# Note down:
# - Publishable Key (pk_live_...)
# - Secret Key (sk_live_...)
# - JWKS URL
```

### 1.2 Configure Clerk Settings
- Enable Email/Password authentication
- Enable OAuth providers (Google, GitHub)
- Set up organizations (for multi-tenancy)
- Configure roles and permissions:
  ```json
  {
    "roles": ["admin", "developer", "viewer"],
    "permissions": [
      "capsule:create",
      "capsule:read",
      "capsule:update",
      "capsule:delete",
      "metrics:read",
      "admin:all"
    ]
  }
  ```

## Step 2: Deploy Backend to Railway

### 2.1 Prepare Railway Project
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway new qlp-backend
```

### 2.2 Configure Railway Services

Create these services in Railway:

1. **Main Application**
```yaml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn src.orchestrator.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/v2/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

2. **PostgreSQL** (Add from Railway dashboard)
3. **Redis** (Add from Railway dashboard)
4. **Temporal** (Deploy using docker-compose)

### 2.3 Set Environment Variables
```bash
# In Railway dashboard or CLI
railway variables set CLERK_SECRET_KEY=sk_live_...
railway variables set CLERK_PUBLISHABLE_KEY=pk_live_...
railway variables set AZURE_OPENAI_API_KEY=...
railway variables set AZURE_OPENAI_ENDPOINT=...
railway variables set OPENAI_API_KEY=sk-...
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set SENTRY_DSN=...
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
```

### 2.4 Deploy
```bash
# Deploy from local
railway up

# Or connect GitHub repo for auto-deploy
railway link
railway github:connect
```

## Step 3: Deploy Frontend to Vercel

### 3.1 Prepare Frontend
```bash
# Create Next.js frontend (if not exists)
npx create-next-app@latest qlp-frontend --typescript --tailwind --app

# Install Clerk
npm install @clerk/nextjs

# Configure Clerk in app/layout.tsx
```

### 3.2 Environment Configuration
```bash
# .env.production
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_API_URL=https://qlp-backend.railway.app/api/v2
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

### 3.3 Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod

# Set environment variables in Vercel dashboard
```

## Step 4: Configure Production Database

### 4.1 Database Migrations
```sql
-- Create production schema
CREATE SCHEMA IF NOT EXISTS qlp_production;

-- Create tables
CREATE TABLE qlp_production.capsules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    manifest JSONB NOT NULL,
    source_code JSONB NOT NULL,
    tests JSONB NOT NULL,
    documentation JSONB NOT NULL,
    infrastructure JSONB NOT NULL,
    validation_report JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_capsules_tenant_id ON qlp_production.capsules(tenant_id);
CREATE INDEX idx_capsules_user_id ON qlp_production.capsules(user_id);
CREATE INDEX idx_capsules_status ON qlp_production.capsules(status);
CREATE INDEX idx_capsules_created_at ON qlp_production.capsules(created_at);

-- Create audit table
CREATE TABLE qlp_production.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255),
    details JSONB NOT NULL DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.2 Configure Backups
```bash
# Railway automatic backups
# Enable in dashboard: Settings > Backups

# Additional backup script
#!/bin/bash
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
# Upload to Azure Blob Storage
```

## Step 5: Configure Monitoring

### 5.1 Sentry Setup
```python
# In src/orchestrator/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[
        FastApiIntegration(transaction_style="endpoint"),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,
    environment=settings.ENVIRONMENT,
    release=f"qlp@{settings.VERSION}"
)
```

### 5.2 Prometheus + Grafana
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
```

### 5.3 Configure Alerts
```yaml
# prometheus/alerts.yml
groups:
  - name: qlp_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(qlp_http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, qlp_http_request_duration_seconds) > 1
        for: 10m
        annotations:
          summary: "95th percentile response time > 1s"
```

## Step 6: Security Hardening

### 6.1 API Security
- ✅ Rate limiting with Redis
- ✅ JWT authentication with Clerk
- ✅ CORS properly configured
- ✅ Security headers implemented
- ✅ Request validation
- ✅ SQL injection prevention

### 6.2 Infrastructure Security
```bash
# Railway security
- Enable 2FA on Railway account
- Use Railway private networking
- Enable SSL/TLS (automatic)

# Environment variables
- Never commit secrets
- Use Railway secrets management
- Rotate keys regularly
```

### 6.3 Data Security
```python
# Encryption at rest
ENCRYPTION_KEY = Fernet.generate_key()
fernet = Fernet(ENCRYPTION_KEY)

# Encrypt sensitive data
encrypted_data = fernet.encrypt(sensitive_data.encode())

# PII handling
- Mask sensitive data in logs
- Implement GDPR compliance
- Regular security audits
```

## Step 7: Performance Optimization

### 7.1 Caching Strategy
```python
# Redis caching
@cache.memoize(timeout=300)
async def get_capsule(capsule_id: str):
    return await db.get_capsule(capsule_id)

# HTTP caching
response.headers["Cache-Control"] = "private, max-age=300"
response.headers["ETag"] = generate_etag(content)
```

### 7.2 Database Optimization
```sql
-- Connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

-- Query optimization
EXPLAIN ANALYZE SELECT ...

-- Partitioning for large tables
CREATE TABLE capsules_2024_01 PARTITION OF capsules
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 7.3 Auto-scaling
```yaml
# Railway auto-scaling
- Horizontal scaling based on CPU/memory
- Min instances: 2
- Max instances: 10
- Target CPU: 70%
```

## Step 8: Deployment Checklist

### Pre-deployment
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] API keys obtained
- [ ] Monitoring configured
- [ ] Backups configured
- [ ] Security review completed

### Deployment
- [ ] Deploy database migrations
- [ ] Deploy backend to Railway
- [ ] Test health endpoints
- [ ] Deploy frontend to Vercel
- [ ] Configure DNS
- [ ] Enable SSL certificates
- [ ] Test authentication flow
- [ ] Test API endpoints
- [ ] Verify monitoring

### Post-deployment
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify backups working
- [ ] Update status page
- [ ] Notify team
- [ ] Monitor for 24 hours

## Step 9: Maintenance

### Regular Tasks
- **Daily**: Check error logs, monitor metrics
- **Weekly**: Review performance, update dependencies
- **Monthly**: Security patches, backup verification
- **Quarterly**: Security audit, performance review

### Incident Response
1. **Detection**: Monitoring alerts
2. **Assessment**: Check severity
3. **Communication**: Update status page
4. **Resolution**: Fix issue
5. **Post-mortem**: Document learnings

## Step 10: Scaling Considerations

### When to Scale
- Response time > 500ms (p95)
- CPU usage > 80%
- Memory usage > 85%
- Queue depth > 1000
- Error rate > 1%

### How to Scale
1. **Vertical**: Increase Railway instance size
2. **Horizontal**: Add more instances
3. **Database**: Read replicas, sharding
4. **Caching**: More Redis instances
5. **CDN**: For static assets

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check Clerk configuration
   - Verify JWKS URL
   - Check token expiration

2. **Database Connection**
   - Check connection string
   - Verify SSL mode
   - Check connection pool

3. **Performance Issues**
   - Enable query logging
   - Check N+1 queries
   - Review caching

4. **Deployment Failures**
   - Check build logs
   - Verify environment variables
   - Test locally first

## Support

- **Documentation**: https://docs.quantumlayerplatform.com
- **Status Page**: https://status.quantumlayerplatform.com
- **Support Email**: support@quantumlayerplatform.com
- **Emergency**: Use PagerDuty integration

---

## Quick Commands Reference

```bash
# Deploy to Railway
railway up

# Check logs
railway logs

# SSH into container
railway run bash

# Run migrations
railway run python -m alembic upgrade head

# Scale service
railway scale web=3

# Restart service
railway restart

# View metrics
railway metrics
```

Remember: Always test in staging before deploying to production!