#!/bin/bash
# Build and push multi-architecture Docker images for QLP with Temporal Cloud support

set -e

# Docker Hub registry
REGISTRY="satishgoda"
VERSION="temporal-cloud-v1"

echo "========================================"
echo "Building Multi-Architecture Docker Images"
echo "Version: $VERSION"
echo "Registry: $REGISTRY"
echo "========================================"

# Ensure we're logged in to Docker Hub
echo "Checking Docker Hub login..."
docker login

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
  --tag $REGISTRY/qlp-orchestrator:$VERSION \
  --tag $REGISTRY/qlp-orchestrator:latest \
  --push \
  -f deployments/docker/orchestrator.dockerfile \
  .

# Build and push temporal worker
echo ""
echo "Building temporal worker image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $REGISTRY/qlp-temporal-worker:$VERSION \
  --tag $REGISTRY/qlp-temporal-worker:latest \
  --push \
  -f deployments/docker/temporal-worker.dockerfile \
  .

# Build and push agent factory
echo ""
echo "Building agent factory image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $REGISTRY/qlp-agent-factory:$VERSION \
  --tag $REGISTRY/qlp-agent-factory:latest \
  --push \
  -f deployments/docker/agent-factory.dockerfile \
  .

# Build and push validation mesh
echo ""
echo "Building validation mesh image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $REGISTRY/qlp-validation-mesh:$VERSION \
  --tag $REGISTRY/qlp-validation-mesh:latest \
  --push \
  -f deployments/docker/validation-mesh.dockerfile \
  .

# Build and push vector memory
echo ""
echo "Building vector memory image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $REGISTRY/qlp-vector-memory:$VERSION \
  --tag $REGISTRY/qlp-vector-memory:latest \
  --push \
  -f deployments/docker/vector-memory.dockerfile \
  .

# Build and push execution sandbox
echo ""
echo "Building execution sandbox image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $REGISTRY/qlp-execution-sandbox:$VERSION \
  --tag $REGISTRY/qlp-execution-sandbox:latest \
  --push \
  -f deployments/docker/execution-sandbox.dockerfile \
  .

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo "Images pushed:"
echo "- $REGISTRY/qlp-orchestrator:$VERSION"
echo "- $REGISTRY/qlp-temporal-worker:$VERSION"
echo "- $REGISTRY/qlp-agent-factory:$VERSION"
echo "- $REGISTRY/qlp-validation-mesh:$VERSION"
echo "- $REGISTRY/qlp-vector-memory:$VERSION"
echo "- $REGISTRY/qlp-execution-sandbox:$VERSION"
echo ""
echo "All images are tagged with both '$VERSION' and 'latest'"
echo "Architectures: linux/amd64, linux/arm64"
echo ""
echo "Next steps:"
echo "1. Deploy to AKS: cd deployments/kubernetes/aks/temporal-cloud && ./deploy-temporal-cloud.sh"
echo "2. Test the deployment: kubectl logs -n qlp-production -l app=qlp-temporal-worker"