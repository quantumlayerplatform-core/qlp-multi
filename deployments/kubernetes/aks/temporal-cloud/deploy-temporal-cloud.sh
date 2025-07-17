#!/bin/bash
# Deploy QLP with Temporal Cloud integration

echo "========================================"
echo "Deploying QLP with Temporal Cloud"
echo "Using Azure Container Registry: qlpregistry.azurecr.io"
echo "========================================"

# Ensure AKS has access to ACR
echo "Ensuring AKS can pull from ACR..."
az aks update -n qlp-aks -g qlp-rg --attach-acr qlpregistry

# Set namespace
NAMESPACE="qlp-production"

# Create namespace if it doesn't exist
echo "Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Deploy Temporal Cloud credentials
echo "Deploying Temporal Cloud credentials..."
kubectl apply -f temporal-cloud-secret.yaml

# Deploy PostgreSQL
echo "Deploying PostgreSQL..."
kubectl apply -f ../postgres-deployment.yaml

# Deploy Redis
echo "Deploying Redis..."
kubectl apply -f ../redis-deployment.yaml

# Deploy Qdrant
echo "Deploying Qdrant..."
kubectl apply -f ../qdrant-deployment.yaml

# Wait for databases to be ready
echo "Waiting for databases to be ready..."
kubectl wait --for=condition=ready pod -l app=qlp-postgres -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=qlp-redis -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=qlp-qdrant -n $NAMESPACE --timeout=300s

# Deploy core services with Temporal Cloud configuration
echo "Deploying Orchestrator with Temporal Cloud..."
kubectl apply -f orchestrator-deployment.yaml

echo "Deploying Agent Factory..."
kubectl apply -f ../agent-factory-deployment.yaml

echo "Deploying Validation Mesh..."
kubectl apply -f ../validation-mesh-deployment.yaml

echo "Deploying Vector Memory..."
kubectl apply -f ../vector-memory-deployment.yaml

echo "Deploying Execution Sandbox..."
kubectl apply -f ../execution-sandbox-deployment.yaml

# Deploy Temporal Worker with Cloud configuration
echo "Deploying Temporal Worker with Cloud connection..."
kubectl apply -f temporal-worker-deployment.yaml

# Wait for all services to be ready
echo "Waiting for services to be ready..."
kubectl wait --for=condition=ready pod -l app=qlp-orchestrator -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=qlp-agent-factory -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=qlp-temporal-worker -n $NAMESPACE --timeout=300s

# Show deployment status
echo ""
echo "========================================"
echo "Deployment Status"
echo "========================================"
kubectl get pods -n $NAMESPACE
echo ""
kubectl get svc -n $NAMESPACE
echo ""

# Show Temporal Worker logs to verify Cloud connection
echo "========================================"
echo "Temporal Worker Logs (Cloud Connection)"
echo "========================================"
kubectl logs -n $NAMESPACE -l app=qlp-temporal-worker --tail=20

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "To access the orchestrator API:"
echo "kubectl port-forward -n $NAMESPACE svc/qlp-orchestrator 8000:8000"
echo ""
echo "Or through the Application Gateway:"
echo "http://85.210.217.253"
echo ""
echo "To check Temporal Cloud connection:"
echo "kubectl logs -n $NAMESPACE -l app=qlp-temporal-worker -f"