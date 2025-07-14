# HAP Production Deployment Guide

This guide provides step-by-step instructions for deploying the HAP (Hate, Abuse, Profanity) system to production.

## Prerequisites

- Access to production database
- Docker registry credentials
- Production environment variables
- Kubernetes cluster access (if using K8s)

## Deployment Steps

### 1. Database Migration

First, apply the HAP database schema to your production database.

#### For Docker Compose Deployment:

```bash
# Connect to production database container
docker exec -it qlp-postgres psql -U qlp_user -d qlp_db

# Apply migration
\i /migrations/004_create_hap_tables_fixed.sql

# Verify tables were created
\dt hap_*
```

#### For Kubernetes Deployment:

```bash
# Copy migration file to pod
kubectl cp migrations/004_create_hap_tables_fixed.sql postgres-pod:/tmp/

# Execute migration
kubectl exec -it postgres-pod -- psql -U qlp_user -d qlp_db -f /tmp/004_create_hap_tables_fixed.sql

# Verify
kubectl exec -it postgres-pod -- psql -U qlp_user -d qlp_db -c "\dt hap_*"
```

#### For Direct Database Connection:

```bash
# Using psql directly
PGPASSWORD=your_password psql -h your-db-host -U qlp_user -d qlp_db -f migrations/004_create_hap_tables_fixed.sql
```

### 2. Update Docker Images

Build and push updated Docker images with HAP integration:

```bash
# Build production image
docker build -t your-registry/qlp-platform:latest -f Dockerfile .

# Tag with version
docker tag your-registry/qlp-platform:latest your-registry/qlp-platform:v2.1.0-hap

# Push to registry
docker push your-registry/qlp-platform:latest
docker push your-registry/qlp-platform:v2.1.0-hap
```

### 3. Configure Environment Variables

Add these HAP-specific environment variables to your production configuration:

```bash
# HAP Configuration
HAP_ENABLED=true
HAP_CACHE_TTL=3600
HAP_LOG_VIOLATIONS=true
HAP_BLOCK_SEVERITY=HIGH  # Block HIGH and CRITICAL
HAP_ML_ENABLED=false     # Enable when ML models are ready
HAP_LLM_CHECKS=false     # Enable for complex content analysis

# Redis Configuration (if not already set)
REDIS_URL=redis://your-redis-host:6379/0

# Performance Tuning
HAP_MAX_CACHE_SIZE=10000
HAP_BATCH_SIZE=100
HAP_TIMEOUT_MS=500
```

### 4. Update Deployment Configuration

#### Docker Compose:

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  orchestrator:
    image: your-registry/qlp-platform:v2.1.0-hap
    environment:
      HAP_ENABLED: "true"
      HAP_CACHE_TTL: "3600"
      HAP_LOG_VIOLATIONS: "true"
      HAP_BLOCK_SEVERITY: "HIGH"
      # ... other env vars
    volumes:
      - ./migrations:/migrations:ro
```

#### Kubernetes:

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qlp-orchestrator
spec:
  template:
    spec:
      containers:
      - name: orchestrator
        image: your-registry/qlp-platform:v2.1.0-hap
        env:
        - name: HAP_ENABLED
          value: "true"
        - name: HAP_CACHE_TTL
          value: "3600"
        - name: HAP_LOG_VIOLATIONS
          value: "true"
        - name: HAP_BLOCK_SEVERITY
          value: "HIGH"
```

### 5. Deployment Process

#### Rolling Update (Recommended):

```bash
# Docker Compose
docker-compose -f docker-compose.production.yml up -d --no-deps --scale orchestrator=2 orchestrator
# Wait for health checks
docker-compose -f docker-compose.production.yml up -d --no-deps orchestrator
docker-compose -f docker-compose.production.yml stop orchestrator_old

# Kubernetes
kubectl set image deployment/qlp-orchestrator orchestrator=your-registry/qlp-platform:v2.1.0-hap
kubectl rollout status deployment/qlp-orchestrator
```

#### Blue-Green Deployment:

1. Deploy new version alongside existing
2. Test new version thoroughly
3. Switch traffic to new version
4. Keep old version for quick rollback

### 6. Post-Deployment Verification

```bash
# 1. Check service health
curl https://your-api.com/health

# 2. Test HAP endpoint directly
curl -X POST https://your-api.com/api/v2/hap/check \
  -H "Content-Type: application/json" \
  -d '{"content": "test content", "context": "user_request"}'

# 3. Test blocking functionality
curl -X POST https://your-api.com/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test",
    "user_id": "test_user", 
    "description": "Create a function [inappropriate content test]"
  }'

# 4. Check logs for HAP activity
docker logs qlp-orchestrator | grep -i hap
# or
kubectl logs deployment/qlp-orchestrator | grep -i hap
```

### 7. Monitor Performance Impact

#### Key Metrics to Monitor:

1. **Response Time**
   - Baseline: Average response time before HAP
   - Target: < 50ms additional latency
   - Alert threshold: > 100ms additional latency

2. **Cache Hit Rate**
   ```sql
   -- Monitor Redis cache hits
   MONITOR
   -- Look for hap:check:* keys
   ```

3. **Database Load**
   ```sql
   -- Check violation logging impact
   SELECT count(*), avg(created_at - now()) as avg_age
   FROM hap_violations
   WHERE created_at > now() - interval '1 hour';
   ```

4. **Memory Usage**
   - Monitor Redis memory consumption
   - Check for memory leaks in services

#### Monitoring Dashboard Queries:

```sql
-- Violations by severity (last 24h)
SELECT severity, count(*) 
FROM hap_violations 
WHERE created_at > now() - interval '24 hours'
GROUP BY severity;

-- Top violating users
SELECT user_id, count(*) as violations
FROM hap_violations
WHERE created_at > now() - interval '7 days'
GROUP BY user_id
ORDER BY violations DESC
LIMIT 10;

-- Response time impact
SELECT 
  date_trunc('hour', created_at) as hour,
  avg(processing_time_ms) as avg_time,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time
FROM hap_violations
GROUP BY hour
ORDER BY hour DESC;
```

### 8. Rollback Plan

If issues arise:

```bash
# Quick rollback - Docker Compose
docker-compose -f docker-compose.production.yml up -d --no-deps orchestrator:previous

# Quick rollback - Kubernetes  
kubectl rollout undo deployment/qlp-orchestrator

# Disable HAP without rollback
# Set HAP_ENABLED=false and restart services
```

### 9. Performance Tuning

After initial deployment, tune these parameters based on observed metrics:

```bash
# Adjust cache TTL based on hit rate
HAP_CACHE_TTL=7200  # Increase if high hit rate

# Adjust blocking threshold if needed
HAP_BLOCK_SEVERITY=MEDIUM  # More restrictive
HAP_BLOCK_SEVERITY=CRITICAL  # Less restrictive

# Enable ML checks for better accuracy
HAP_ML_ENABLED=true  # When ready

# Batch processing for high volume
HAP_BATCH_ENABLED=true
HAP_BATCH_SIZE=50
HAP_BATCH_DELAY_MS=100
```

## Troubleshooting

### Common Issues:

1. **High latency after deployment**
   - Check Redis connectivity
   - Verify cache is working: `redis-cli KEYS "hap:*"`
   - Reduce HAP_TIMEOUT_MS if needed

2. **Database connection errors**
   - Verify asyncpg is installed
   - Check connection string has `postgresql+asyncpg://`
   - Verify database user has required permissions

3. **Memory issues**
   - Monitor Redis memory: `redis-cli INFO memory`
   - Implement cache eviction if needed
   - Check for connection leaks

### Debug Commands:

```bash
# Check HAP service initialization
docker logs qlp-orchestrator 2>&1 | grep "HAP service initialized"

# Monitor real-time violations
watch -n 5 'psql -h localhost -U qlp_user -d qlp_db -c "SELECT created_at, severity, categories FROM hap_violations ORDER BY created_at DESC LIMIT 10"'

# Check cache effectiveness
redis-cli --stat
```

## Next Steps

After successful deployment:

1. Monitor for 24-48 hours
2. Analyze violation patterns
3. Adjust severity thresholds based on false positives
4. Plan ML model integration
5. Set up automated reports for compliance team