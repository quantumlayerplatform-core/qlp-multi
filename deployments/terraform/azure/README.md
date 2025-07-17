# QLP Azure Kubernetes Service (AKS) Deployment

This directory contains the Terraform configuration and deployment scripts for deploying the Quantum Layer Platform (QLP) to Azure Kubernetes Service (AKS) in the UK South region.

## Architecture Overview

The deployment creates the following Azure resources:

- **AKS Cluster**: Multi-node Kubernetes cluster with autoscaling
- **Azure Container Registry (ACR)**: Private Docker registry with geo-replication
- **PostgreSQL Flexible Server**: Managed PostgreSQL with high availability
- **Azure Redis Cache**: Managed Redis with zone redundancy
- **Cosmos DB**: Document storage for capsules
- **Azure Service Bus**: Message queuing system
- **Azure Key Vault**: Secure secrets management
- **Storage Account**: Blob storage for artifacts
- **Application Insights**: Application monitoring
- **Log Analytics**: Centralized logging

## Prerequisites

1. **Azure CLI** installed and configured
2. **Terraform** >= 1.3.0
3. **kubectl** installed
4. **Docker** with buildx support
5. **Helm** >= 3.0
6. **An Azure subscription** with sufficient quota

## Quick Start

1. **Clone and navigate to the deployment directory:**
   ```bash
   cd deployments/terraform/azure
   ```

2. **Copy and configure the variables:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your configuration
   ```

3. **Run the deployment script:**
   ```bash
   ./scripts/deploy-aks.sh
   ```

## Manual Deployment Steps

### 1. Infrastructure Deployment (Terraform)

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -out=tfplan

# Apply the configuration
terraform apply tfplan
```

### 2. Build and Push Docker Images

```bash
# Get ACR login server
ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)

# Login to ACR
az acr login --name ${ACR_LOGIN_SERVER%%.*}

# Build and push multi-architecture images
./scripts/build-multiarch.sh \
  --registry $ACR_LOGIN_SERVER \
  --tag latest \
  --push \
  --platforms linux/amd64,linux/arm64
```

### 3. Deploy to Kubernetes

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group qlp-production \
  --name qlp-aks-production

# Deploy Kubernetes resources
kubectl apply -f deployments/kubernetes/aks/
```

## Configuration

### Required Variables

Update `terraform.tfvars` with:

- `postgres_admin_password`: Strong password for PostgreSQL
- `ops_email`: Email for alerts
- `slack_webhook_url`: Slack webhook for notifications
- `domain`: Your domain name for ingress
- `github_token`: GitHub token for ACR tasks (optional)

### Environment Variables

Create `.env.production` with:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key

# Alternative LLMs (optional)
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# GitHub Integration
GITHUB_TOKEN=your-token

# AWS Bedrock (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

## Multi-Architecture Support

The platform supports both AMD64 and ARM64 architectures:

- **AMD64**: Standard x86_64 processors
- **ARM64**: ARM-based processors (more cost-effective)

Build for specific architectures:
```bash
# AMD64 only
./scripts/build-multiarch.sh --platforms linux/amd64

# ARM64 only
./scripts/build-multiarch.sh --platforms linux/arm64
```

## Monitoring and Observability

### Accessing Monitoring Tools

1. **Grafana** (Metrics Dashboard):
   ```bash
   # Get admin password
   terraform output -raw grafana_admin_password
   # Access at: https://grafana.qlp.yourdomain.com
   ```

2. **Jaeger** (Distributed Tracing):
   ```bash
   # Access at: https://jaeger.qlp.yourdomain.com
   ```

3. **Temporal UI** (Workflow Management):
   ```bash
   # Get ingress IP
   kubectl get service nginx-ingress-controller -n ingress-nginx
   # Access at: http://<INGRESS_IP>:8088
   ```

### Azure Monitor Integration

- **Application Insights**: Automatic APM integration
- **Log Analytics**: Centralized logging with custom queries
- **Alerts**: Configured for high CPU, pod failures, and errors

## Security Considerations

1. **Network Security**:
   - Private endpoints for databases
   - Network policies for pod-to-pod communication
   - NSG rules for subnet isolation

2. **Secrets Management**:
   - Azure Key Vault integration
   - Kubernetes Secret Store CSI driver
   - Workload identity for pod authentication

3. **RBAC**:
   - Service accounts with minimal permissions
   - Azure AD integration for user access

## Scaling

### Horizontal Pod Autoscaling

```bash
# Enable HPA for services
kubectl autoscale deployment orchestrator \
  --cpu-percent=70 \
  --min=3 \
  --max=10 \
  -n qlp-production
```

### Cluster Autoscaling

The AKS cluster automatically scales nodes between 3-10 based on workload.

## Troubleshooting

### Check Service Health

```bash
# Check pod status
kubectl get pods -n qlp-production

# View logs
kubectl logs -f deployment/orchestrator -n qlp-production

# Check service endpoints
kubectl get endpoints -n qlp-production
```

### Common Issues

1. **Image Pull Errors**:
   ```bash
   # Verify ACR access
   az acr repository list --name qlpregistryproduction
   ```

2. **Database Connection Issues**:
   ```bash
   # Check PostgreSQL connectivity
   kubectl exec -it deployment/orchestrator -n qlp-production -- nc -zv <postgres-fqdn> 5432
   ```

3. **Ingress Not Working**:
   ```bash
   # Check ingress controller
   kubectl get service nginx-ingress-controller -n ingress-nginx
   ```

## Maintenance

### Backup and Restore

1. **PostgreSQL Backup**:
   - Automated daily backups with 35-day retention
   - Geo-redundant backup storage

2. **Cosmos DB Backup**:
   - Continuous backup with 30-day retention
   - Point-in-time restore capability

### Updates

```bash
# Update Kubernetes deployments
kubectl set image deployment/orchestrator \
  orchestrator=<acr>.azurecr.io/qlp-orchestrator:new-tag \
  -n qlp-production

# Rolling update with zero downtime
kubectl rollout status deployment/orchestrator -n qlp-production
```

## Cost Optimization

1. **Use Spot Instances** for non-critical workloads
2. **Enable autoscaling** to scale down during low usage
3. **Use ARM64 nodes** for better price/performance
4. **Configure resource limits** to prevent overprovisioning

## Support

For issues or questions:
1. Check the [troubleshooting guide](#troubleshooting)
2. Review Azure Monitor dashboards
3. Check Temporal UI for workflow failures
4. Contact the platform team