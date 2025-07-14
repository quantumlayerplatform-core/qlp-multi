# HAP Rollback Plan

## Quick Rollback Procedures

### 1. Disable HAP Without Rollback (Fastest)

If HAP is causing issues but services are still running:

```bash
# Docker Compose
docker exec qlp-orchestrator sh -c 'export HAP_ENABLED=false'
docker-compose restart orchestrator

# Kubernetes
kubectl set env deployment/qlp-orchestrator-hap HAP_ENABLED=false
```

### 2. Full Service Rollback

#### Docker Compose:
```bash
# Roll back to previous image
docker-compose -f docker-compose.platform.yml up -d \
  --no-deps orchestrator:v2.0.0

# Verify rollback
docker logs qlp-orchestrator | tail -20
```

#### Kubernetes:
```bash
# Automatic rollback
kubectl rollout undo deployment/qlp-orchestrator-hap

# Check rollback status
kubectl rollout status deployment/qlp-orchestrator-hap

# Verify pods are running old version
kubectl get pods -l app=qlp-orchestrator -o jsonpath='{.items[*].spec.containers[*].image}'
```

### 3. Database Rollback (if needed)

**WARNING**: This will lose all HAP violation data!

```sql
-- Drop HAP tables and related objects
DROP VIEW IF EXISTS hap_high_risk_users CASCADE;
DROP VIEW IF EXISTS hap_recent_violations CASCADE;
DROP TRIGGER IF EXISTS trigger_update_risk_score ON hap_violations;
DROP FUNCTION IF EXISTS update_user_risk_score();
DROP TABLE IF EXISTS hap_statistics CASCADE;
DROP TABLE IF EXISTS hap_user_risk_scores CASCADE;
DROP TABLE IF EXISTS hap_whitelist CASCADE;
DROP TABLE IF EXISTS hap_custom_rules CASCADE;
DROP TABLE IF EXISTS hap_violations CASCADE;
```

## Rollback Decision Matrix

| Symptom | Severity | Action | Rollback Needed |
|---------|----------|--------|-----------------|
| High latency (>100ms added) | Low | Tune HAP_TIMEOUT_MS | No |
| Some false positives | Low | Adjust HAP_BLOCK_SEVERITY | No |
| Redis connection issues | Medium | Fix Redis config | No |
| Service crashes | High | Disable HAP_ENABLED | Maybe |
| Database overload | High | Disable logging or rollback | Yes |
| Complete service failure | Critical | Full rollback | Yes |

## Post-Rollback Checklist

1. **Verify Services**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   ```

2. **Check Logs**:
   ```bash
   docker logs qlp-orchestrator | grep -i error
   ```

3. **Monitor Performance**:
   - Response times should return to baseline
   - Error rates should drop to normal
   - CPU/Memory usage should stabilize

4. **Notify Team**:
   - Send rollback notification
   - Document issue that caused rollback
   - Plan fix for next deployment

## Common Issues and Fixes

### Issue: "asyncpg driver not found"
**Fix**: Ensure requirements.txt includes `asyncpg`

### Issue: "HAP service initialization failed"
**Fix**: Check Redis connectivity and DATABASE_URL format

### Issue: "High memory usage"
**Fix**: Reduce HAP_MAX_CACHE_SIZE or implement cache eviction

### Issue: "Too many false positives"
**Fix**: Adjust HAP_BLOCK_SEVERITY to CRITICAL only

## Recovery Plan

After rollback, to prepare for re-deployment:

1. **Analyze Logs**:
   ```bash
   # Collect logs from failed deployment
   docker logs qlp-orchestrator > hap_failure_logs.txt
   
   # Look for patterns
   grep -i "hap\|error\|exception" hap_failure_logs.txt
   ```

2. **Fix Issues**:
   - Address root cause
   - Update configuration
   - Add more comprehensive tests

3. **Test in Staging**:
   - Deploy to staging first
   - Run load tests
   - Verify all features work

4. **Gradual Re-deployment**:
   - Deploy to one instance first
   - Monitor for 1 hour
   - Roll out to remaining instances