#!/bin/bash
# Build and push multi-architecture Docker images to Azure Container Registry

set -e

# Azure Container Registry settings
ACR_NAME="qlpregistry"
ACR_REGISTRY="$ACR_NAME.azurecr.io"
VERSION="temporal-cloud-v1"

echo "========================================"
echo "Building Multi-Architecture Docker Images for Azure"
echo "Version: $VERSION"
echo "Registry: $ACR_REGISTRY"
echo "========================================"

# Login to Azure Container Registry
echo "Logging in to Azure Container Registry..."
az acr login --name $ACR_NAME

# Create builder if it doesn't exist
echo "Setting up Docker buildx..."
docker buildx create --name qlp-builder --use 2>/dev/null || docker buildx use qlp-builder

# Ensure the builder supports multi-arch
docker buildx inspect --bootstrap

# Build and push orchestrator
echo ""
echo "Building orchestrator image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ACR_REGISTRY/qlp/orchestrator:$VERSION \
  --tag $ACR_REGISTRY/qlp/orchestrator:latest \
  --push \
  -f services/orchestrator/Dockerfile \
  .

# Build and push temporal worker
echo ""
echo "Building temporal worker image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ACR_REGISTRY/qlp/temporal-worker:$VERSION \
  --tag $ACR_REGISTRY/qlp/temporal-worker:latest \
  --push \
  -f deployments/docker/Dockerfile.temporal-worker \
  .

# Build and push agent factory
echo ""
echo "Building agent factory image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ACR_REGISTRY/qlp/agent-factory:$VERSION \
  --tag $ACR_REGISTRY/qlp/agent-factory:latest \
  --push \
  -f services/agents/Dockerfile \
  .

# Build and push validation mesh
echo ""
echo "Building validation mesh image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ACR_REGISTRY/qlp/validation-mesh:$VERSION \
  --tag $ACR_REGISTRY/qlp/validation-mesh:latest \
  --push \
  -f services/validation/Dockerfile \
  .

# Build and push vector memory
echo ""
echo "Building vector memory image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ACR_REGISTRY/qlp/vector-memory:$VERSION \
  --tag $ACR_REGISTRY/qlp/vector-memory:latest \
  --push \
  -f services/memory/Dockerfile \
  .

# Build and push execution sandbox
echo ""
echo "Building execution sandbox image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ACR_REGISTRY/qlp/execution-sandbox:$VERSION \
  --tag $ACR_REGISTRY/qlp/execution-sandbox:latest \
  --push \
  -f services/sandbox/Dockerfile \
  .

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo "Images pushed to Azure Container Registry:"
echo "- $ACR_REGISTRY/qlp/orchestrator:$VERSION"
echo "- $ACR_REGISTRY/qlp/temporal-worker:$VERSION"
echo "- $ACR_REGISTRY/qlp/agent-factory:$VERSION"
echo "- $ACR_REGISTRY/qlp/validation-mesh:$VERSION"
echo "- $ACR_REGISTRY/qlp/vector-memory:$VERSION"
echo "- $ACR_REGISTRY/qlp/execution-sandbox:$VERSION"
echo ""
echo "All images are tagged with both '$VERSION' and 'latest'"
echo "Architectures: linux/amd64, linux/arm64"
echo ""
echo "To verify images:"
echo "az acr repository list --name $ACR_NAME --output table"
echo ""
echo "Next steps:"
echo "1. Update Kubernetes manifests to use ACR images"
echo "2. Deploy to AKS: cd deployments/kubernetes/aks/temporal-cloud && ./deploy-temporal-cloud.sh"
echo "3. Test the deployment: kubectl logs -n qlp-production -l app=qlp-temporal-worker"