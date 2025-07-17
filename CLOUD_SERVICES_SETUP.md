# Cloud Services Setup Guide

This guide helps you migrate from local services to managed cloud services before the AKS deployment.

## 1. Supabase Setup (PostgreSQL Replacement)

### Create Supabase Project
1. Go to [https://supabase.com](https://supabase.com)
2. Create a new project in `UK (London)` region
3. Note down:
   - Database URL (Connection String)
   - Database password

### Migrate Data
```bash
# Export from local PostgreSQL
docker exec qlp-postgres pg_dump -U qlp_user qlp_db > qlp_backup.sql

# Import to Supabase
psql -h <supabase-host> -U postgres -d postgres < qlp_backup.sql
```

### Update .env
```bash
SUPABASE_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

## 2. Qdrant Cloud Setup

### Create Qdrant Cloud Cluster
1. Go to [https://cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a new cluster in `EU region`
3. Choose appropriate size (start with smallest)
4. Note down:
   - Cluster URL
   - API Key

### Migrate Vector Data
```bash
# Create snapshot from local Qdrant
curl -X POST http://localhost:6333/collections/qlp_vectors/snapshots

# List snapshots
curl http://localhost:6333/collections/qlp_vectors/snapshots

# Download snapshot
curl http://localhost:6333/collections/qlp_vectors/snapshots/{snapshot_name} -o snapshot.tar

# Upload to Qdrant Cloud
curl -X POST https://[your-cluster].qdrant.io/collections/qlp_vectors/snapshots/upload \
  -H "api-key: YOUR_API_KEY" \
  -F "snapshot=@snapshot.tar"
```

### Update .env
```bash
QDRANT_CLOUD_URL=https://[your-cluster].qdrant.io
QDRANT_CLOUD_API_KEY=your-api-key
```

## 3. Temporal Cloud Setup

### Create Temporal Cloud Account
1. Go to [https://temporal.io/cloud](https://temporal.io/cloud)
2. Create a namespace (e.g., `qlp-production`)
3. Download certificates for mTLS
4. Note down:
   - Namespace endpoint
   - Namespace name

### Configure Temporal Client
```bash
# Save certificates
echo "$TEMPORAL_CLOUD_TLS_CERT" > temporal-cloud.pem
echo "$TEMPORAL_CLOUD_TLS_KEY" > temporal-cloud.key

# Update .env
TEMPORAL_CLOUD_ENDPOINT=qlp-production.a2dd6.tmprl.cloud:7233
TEMPORAL_CLOUD_NAMESPACE=qlp-production
TEMPORAL_CLOUD_TLS_CERT=$(cat temporal-cloud.pem | base64)
TEMPORAL_CLOUD_TLS_KEY=$(cat temporal-cloud.key | base64)
```

## 4. Optional: Redis Cloud

If you want to replace Redis too:

### Create Redis Cloud Database
1. Go to [https://redis.com/cloud](https://redis.com/cloud)
2. Create a database in `UK region`
3. Note down connection string

### Update .env
```bash
REDIS_CLOUD_URL=redis://default:[password]@[endpoint]:[port]
```

## Migration Steps

### 1. Test Cloud Connections
```bash
# Test Supabase
psql "$SUPABASE_DATABASE_URL" -c "SELECT version();"

# Test Qdrant Cloud
curl -H "api-key: $QDRANT_CLOUD_API_KEY" $QDRANT_CLOUD_URL/collections

# Test Temporal Cloud (requires proper client setup)
tctl --namespace $TEMPORAL_CLOUD_NAMESPACE namespace describe
```

### 2. Update Application Code

Create a new configuration file:

```python
# src/common/cloud_config.py
import os
from urllib.parse import urlparse

def get_database_config():
    """Get database configuration for cloud services"""
    db_url = os.getenv('DATABASE_URL', os.getenv('SUPABASE_DATABASE_URL'))
    if db_url:
        parsed = urlparse(db_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],
            'user': parsed.username,
            'password': parsed.password
        }
    return None

def get_qdrant_config():
    """Get Qdrant configuration for cloud"""
    url = os.getenv('QDRANT_URL', os.getenv('QDRANT_CLOUD_URL'))
    api_key = os.getenv('QDRANT_API_KEY', os.getenv('QDRANT_CLOUD_API_KEY'))
    
    return {
        'url': url,
        'api_key': api_key,
        'use_cloud': bool(api_key)
    }

def get_temporal_config():
    """Get Temporal configuration for cloud"""
    endpoint = os.getenv('TEMPORAL_SERVER', os.getenv('TEMPORAL_CLOUD_ENDPOINT'))
    namespace = os.getenv('TEMPORAL_NAMESPACE', os.getenv('TEMPORAL_CLOUD_NAMESPACE'))
    tls_cert = os.getenv('TEMPORAL_CLOUD_TLS_CERT')
    tls_key = os.getenv('TEMPORAL_CLOUD_TLS_KEY')
    
    return {
        'endpoint': endpoint,
        'namespace': namespace,
        'use_tls': bool(tls_cert and tls_key),
        'tls_cert': tls_cert,
        'tls_key': tls_key
    }
```

### 3. Start Services with Cloud Configuration
```bash
# Stop existing services
docker-compose -f docker-compose.platform.yml down

# Start with cloud services
docker-compose -f docker-compose.cloud-services.yml up -d

# Check health
docker-compose -f docker-compose.cloud-services.yml ps
```

### 4. Verify Everything Works
```bash
# Test orchestrator health
curl http://localhost:8000/health

# Test a simple workflow
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a simple hello world function in Python"}'

# Check logs
docker-compose -f docker-compose.cloud-services.yml logs -f orchestrator
```

## What's Left for AKS?

After migrating to cloud services, only these components need to run in AKS:

1. **Application Services**:
   - orchestrator
   - agent-factory
   - validation-mesh
   - vector-memory
   - execution-sandbox
   - temporal-worker
   - marketing-worker

2. **Infrastructure**:
   - NGINX Ingress Controller
   - Redis (or migrate to Redis Cloud)

This significantly simplifies the AKS deployment:
- No StatefulSets needed
- No persistent volumes
- No database backups to manage
- Easier scaling and updates

## Rollback Plan

If something doesn't work:

```bash
# Quick rollback to local services
docker-compose -f docker-compose.platform.yml up -d

# Your data is safe in cloud services
# Just update .env to point back to local services
```

## Cost Estimates (Monthly)

- **Supabase**: Free tier (up to 500MB) or ~$25/month
- **Qdrant Cloud**: ~$50-100/month (depending on size)
- **Temporal Cloud**: ~$200/month (pay per action)
- **Redis Cloud**: Free tier (30MB) or ~$15/month

Total: ~$300/month for managed services vs managing yourself

## Next Steps

1. Set up each cloud service
2. Migrate data
3. Test with docker-compose.cloud-services.yml
4. Once stable, deploy only app services to AKS
5. Point AKS to same cloud services

This approach gives you:
- ✅ Managed databases (no backups needed)
- ✅ High availability built-in
- ✅ Simpler AKS deployment
- ✅ Easy rollback options
- ✅ Professional support from cloud providers