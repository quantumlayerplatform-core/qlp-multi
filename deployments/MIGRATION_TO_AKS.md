# Migration Guide: Docker Compose to AKS

## Current Local Setup vs AKS Deployment

Your current Docker Compose setup includes all services needed. Here's how they map to AKS:

### Service Mapping

| Docker Compose Service | AKS Deployment | Notes |
|------------------------|----------------|--------|
| qlp-postgres | Azure PostgreSQL Flexible Server | Managed service, better for production |
| qlp-redis | Azure Redis Cache | Managed service with HA |
| qlp-qdrant | Qdrant StatefulSet | Runs in K8s with persistent storage |
| qlp-temporal | Temporal StatefulSet | Runs in K8s |
| qlp-temporal-ui | Temporal UI Deployment | Runs in K8s |
| qlp-temporal-worker | Temporal Worker Deployment | Scaled in K8s |
| qlp-orchestrator | Orchestrator Deployment | Main API service |
| qlp-agent-factory | Agent Factory Deployment | Scaled for AI workloads |
| qlp-validation-mesh | Validation Mesh Deployment | Validation service |
| qlp-vector-memory | Vector Memory Deployment | Memory service |
| qlp-execution-sandbox | Execution Sandbox Deployment | Code execution |
| qlp-nginx | NGINX Ingress Controller | K8s native ingress |
| qlp-marketing-worker | Marketing Worker Deployment | Marketing automation |
| qlp-pgadmin | Not deployed | Use Azure Portal or local pgAdmin |
| qlp-prometheus | Prometheus (Helm) | K8s native monitoring |
| qlp-grafana | Grafana (Helm) | K8s native dashboards |

## Quick Migration Path

Since you already have working Docker images, here's the fastest path to AKS:

### 1. Tag and Push Existing Images to ACR

```bash
# First, create the ACR using Terraform (minimal)
cd deployments/terraform/azure
terraform apply -target=azurerm_resource_group.main -target=azurerm_container_registry.acr

# Get ACR details
ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
az acr login --name ${ACR_LOGIN_SERVER%%.*}

# Tag and push your existing images
docker tag qlp-orchestrator:latest $ACR_LOGIN_SERVER/qlp-orchestrator:latest
docker tag qlp-agent-factory:latest $ACR_LOGIN_SERVER/qlp-agent-factory:latest
docker tag qlp-validation-mesh:latest $ACR_LOGIN_SERVER/qlp-validation-mesh:latest
docker tag qlp-vector-memory:latest $ACR_LOGIN_SERVER/qlp-vector-memory:latest
docker tag qlp-execution-sandbox:latest $ACR_LOGIN_SERVER/qlp-execution-sandbox:latest
docker tag qlp-temporal-worker:latest $ACR_LOGIN_SERVER/qlp-temporal-worker:latest
docker tag qlp-marketing-worker:latest $ACR_LOGIN_SERVER/qlp-marketing-worker:latest

# Push all images
docker push $ACR_LOGIN_SERVER/qlp-orchestrator:latest
docker push $ACR_LOGIN_SERVER/qlp-agent-factory:latest
docker push $ACR_LOGIN_SERVER/qlp-validation-mesh:latest
docker push $ACR_LOGIN_SERVER/qlp-vector-memory:latest
docker push $ACR_LOGIN_SERVER/qlp-execution-sandbox:latest
docker push $ACR_LOGIN_SERVER/qlp-temporal-worker:latest
docker push $ACR_LOGIN_SERVER/qlp-marketing-worker:latest
```

### 2. Minimal AKS Deployment

For a quick start, you can run most services in K8s while keeping some local:

```bash
# Create minimal AKS cluster
az aks create \
  --resource-group qlp-production \
  --name qlp-aks \
  --node-count 2 \
  --node-vm-size Standard_D4s_v3 \
  --location uksouth \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group qlp-production --name qlp-aks

# Deploy only core services initially
kubectl apply -f deployments/kubernetes/aks/qlp-services.yaml
```

### 3. Hybrid Approach (Recommended for Testing)

Keep some services local while testing AKS:

**Local (Docker Compose):**
- PostgreSQL (until data migration)
- Redis
- Qdrant
- Temporal

**AKS:**
- All QLP application services
- NGINX Ingress

This allows you to test AKS deployment without migrating data immediately.

## Environment Variables Sync

Your current `.env` file needs to be converted to Kubernetes secrets:

```bash
# Create secrets from your existing .env
kubectl create secret generic qlp-secrets \
  --from-env-file=.env \
  --namespace=qlp-production
```

## Data Migration Strategy

### PostgreSQL Migration
```bash
# Backup local PostgreSQL
docker exec qlp-postgres pg_dump -U qlp_user qlp_db > backup.sql

# Restore to Azure PostgreSQL
psql -h <azure-postgres-fqdn> -U qlpadmin -d qlp_db < backup.sql
```

### Qdrant Migration
```bash
# Create snapshot
curl -X POST http://localhost:6333/collections/qlp_vectors/snapshots

# Download and upload to AKS Qdrant
# (After Qdrant is running in AKS)
```

## Quick Test Commands

Test that your services work in AKS:

```bash
# Port forward to test locally
kubectl port-forward service/orchestrator 8000:8000 -n qlp-production

# Test the API
curl http://localhost:8000/health

# Check logs
kubectl logs -f deployment/orchestrator -n qlp-production
```

## Rollback Plan

If something goes wrong:

```bash
# Services are still running locally
docker-compose -f docker-compose.platform.yml ps

# Delete AKS resources but keep ACR
kubectl delete namespace qlp-production

# Or completely remove AKS
az aks delete --name qlp-aks --resource-group qlp-production
```

## Gradual Migration Checklist

- [ ] 1. Create ACR and push images
- [ ] 2. Deploy stateless services to AKS first
- [ ] 3. Test connectivity with local databases
- [ ] 4. Migrate Qdrant to AKS with data
- [ ] 5. Set up Azure PostgreSQL and migrate data
- [ ] 6. Switch Redis to Azure Redis Cache
- [ ] 7. Update DNS to point to AKS ingress
- [ ] 8. Shut down local Docker Compose

## Cost-Saving Tips for Testing

1. **Use a smaller AKS cluster initially:**
   ```bash
   --node-count 1 --node-vm-size Standard_B2s
   ```

2. **Use Basic tier for Azure services during testing:**
   - PostgreSQL: Burstable tier
   - Redis: Basic C0
   - No geo-replication

3. **Delete resources when not testing:**
   ```bash
   # Stop AKS cluster (preserves data)
   az aks stop --name qlp-aks --resource-group qlp-production
   
   # Start when needed
   az aks start --name qlp-aks --resource-group qlp-production
   ```

## Commands to Keep Services in Sync

```bash
# Export Docker Compose config as K8s manifests
kompose convert -f docker-compose.platform.yml -o k8s-converted/

# Compare environment variables
diff <(docker exec qlp-orchestrator env | sort) \
     <(kubectl exec deployment/orchestrator -- env | sort)
```

## Next Steps

1. **For Testing**: Use the hybrid approach - run apps in AKS, databases locally
2. **For Production**: Use full Terraform deployment with managed Azure services
3. **For Development**: Keep Docker Compose for local development

The key is that you don't need to rebuild images - just retag and push your existing ones!