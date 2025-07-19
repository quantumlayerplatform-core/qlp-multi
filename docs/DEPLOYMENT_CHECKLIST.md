# QLP Deployment Checklist

This checklist ensures all necessary configurations are in place before deploying QLP to any environment.

## Pre-Deployment Configuration

### 1. Environment Variables (.env file for Docker Compose)

- [ ] **API Keys**
  - [ ] `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
  - [ ] `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
  - [ ] `OPENAI_API_KEY` - OpenAI API key (fallback)
  - [ ] `ANTHROPIC_API_KEY` - Anthropic API key (optional)
  - [ ] `GROQ_API_KEY` - Groq API key (optional)
  - [ ] `GITHUB_TOKEN` - GitHub personal access token (for GitHub integration)

- [ ] **Critical Configuration**
  - [ ] `TEMPORAL_TASK_QUEUE=qlp-main` - Ensures worker polls correct queue
  - [ ] `AITL_ENABLED=false` - Disable AITL to prevent workflow blocking

### 2. Kubernetes ConfigMaps

For both local Kubernetes (`deployments/kubernetes/configmap.yaml`) and AKS (`deployments/kubernetes/aks/configmap.yaml` and `deployments/kubernetes/aks/00-configmap.yaml`):

- [ ] **Temporal Configuration**
  ```yaml
  TEMPORAL_SERVER: "temporal:7233"
  TEMPORAL_NAMESPACE: "default"
  TEMPORAL_TASK_QUEUE: "qlp-main"
  ```

- [ ] **Feature Flags**
  ```yaml
  TDD_ENABLED: "true"
  AITL_ENABLED: "false"  # Disabled due to overly conservative scoring
  ENTERPRISE_FEATURES_ENABLED: "true"
  ```

### 3. Docker Configuration

- [ ] `.dockerignore` file exists with:
  - [ ] `.venv` and other virtual environments
  - [ ] `.env` files (don't include secrets in images)
  - [ ] `__pycache__` and Python cache files
  - [ ] `logs/` directory
  - [ ] Generated files and local storage

### 4. Database Initialization

- [ ] For Docker Compose:
  ```bash
  python3 init_db_docker.py
  ```
- [ ] For Kubernetes: Ensure init container or job runs database migrations

### 5. Service Health Checks

Before considering deployment successful, verify:

- [ ] All services return healthy status:
  ```bash
  curl http://localhost:8000/health  # Orchestrator
  curl http://localhost:8001/health  # Agent Factory
  curl http://localhost:8002/health  # Validation Mesh
  curl http://localhost:8003/health  # Vector Memory
  curl http://localhost:8004/health  # Execution Sandbox
  ```

- [ ] Temporal UI is accessible:
  ```bash
  open http://localhost:8088
  ```

- [ ] Worker is connected to correct task queue:
  ```bash
  docker logs qlp-temporal-worker | grep "Worker started on task queue: qlp-main"
  ```

## Deployment Steps

### Local Docker Compose

1. [ ] Copy `.env.example` to `.env` and configure all required values
2. [ ] Run: `docker-compose -f docker-compose.platform.yml up -d`
3. [ ] Initialize database: `python3 init_db_docker.py`
4. [ ] Verify all services are healthy
5. [ ] Test with simple request: `./test_complete_flow.sh`

### Local Kubernetes

1. [ ] Create namespace: `kubectl create namespace qlp`
2. [ ] Create secrets for API keys
3. [ ] Apply ConfigMap: `kubectl apply -f deployments/kubernetes/configmap.yaml`
4. [ ] Deploy infrastructure: `kubectl apply -f deployments/kubernetes/infrastructure/`
5. [ ] Deploy services: `kubectl apply -f deployments/kubernetes/services/`
6. [ ] Verify all pods are running: `kubectl get pods -n qlp`

### Azure Kubernetes Service (AKS)

1. [ ] Create namespace: `kubectl create namespace qlp-production`
2. [ ] Create secrets using Azure Key Vault or kubectl
3. [ ] Apply ConfigMaps:
   ```bash
   kubectl apply -f deployments/kubernetes/aks/00-configmap.yaml
   kubectl apply -f deployments/kubernetes/aks/configmap.yaml
   ```
4. [ ] Deploy infrastructure services
5. [ ] Deploy QLP services
6. [ ] Configure Application Gateway ingress (if using)
7. [ ] Verify external access through Application Gateway

## Common Issues and Solutions

### Issue: Workflow Stuck on validate_result_activity
- **Cause**: AITL is enabled and waiting for human approval
- **Solution**: Set `AITL_ENABLED=false` in environment

### Issue: Worker Not Processing Tasks
- **Cause**: Worker polling wrong task queue
- **Solution**: Ensure `TEMPORAL_TASK_QUEUE=qlp-main` is set

### Issue: "relation 'capsules' does not exist"
- **Cause**: Database not initialized
- **Solution**: Run database initialization script

### Issue: Service Connection Refused
- **Cause**: Services not fully started or wrong URLs
- **Solution**: Check service logs and verify service URLs in ConfigMap

## Post-Deployment Verification

1. [ ] Run end-to-end test:
   ```bash
   ./test_complete_flow.sh
   ```

2. [ ] Check Temporal workflows:
   ```bash
   docker exec qlp-temporal temporal workflow list
   ```

3. [ ] Verify capsule creation:
   ```bash
   curl -X POST http://localhost:8000/execute \
     -H "Content-Type: application/json" \
     -d '{"request": "Create a Python function to add two numbers"}'
   ```

4. [ ] Monitor logs for errors:
   ```bash
   docker-compose logs -f  # Docker Compose
   kubectl logs -f -n qlp -l app=orchestrator  # Kubernetes
   ```

## Rollback Plan

If deployment fails:

1. **Docker Compose**: 
   ```bash
   docker-compose -f docker-compose.platform.yml down
   git checkout -- .env  # Restore previous config
   ```

2. **Kubernetes**:
   ```bash
   kubectl rollout undo deployment/orchestrator -n qlp
   kubectl rollout undo deployment/temporal-worker -n qlp
   ```

## Notes

- Always test in a staging environment before production
- Keep API keys secure and use secret management tools
- Monitor resource usage, especially for the execution sandbox
- Consider scaling worker replicas for high load
- Temporal Cloud configuration files exist but are not currently used (self-hosted Temporal preferred)