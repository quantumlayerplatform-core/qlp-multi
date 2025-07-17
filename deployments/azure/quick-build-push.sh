#!/bin/bash
set -euo pipefail

# Quick build script - builds AMD64 only first for speed
# Then optionally builds multi-arch

ACR_LOGIN_SERVER="qlpregistry.azurecr.io"

echo "=== Quick Build & Push to ACR ==="
echo "Building AMD64 only for speed..."

# Array of services to build
SERVICES=(
    "orchestrator:services/orchestrator/Dockerfile"
    "agent-factory:services/agents/Dockerfile"
    "validation-mesh:services/validation/Dockerfile"
    "vector-memory:services/memory/Dockerfile"
    "execution-sandbox:services/sandbox/Dockerfile"
    "temporal-worker:deployments/docker/Dockerfile.temporal-worker"
)

# Build function
build_service() {
    local service_name=$(echo $1 | cut -d: -f1)
    local dockerfile=$(echo $1 | cut -d: -f2)
    local tag="$ACR_LOGIN_SERVER/qlp/$service_name:latest"
    
    echo -e "\n📦 Building $service_name..."
    
    # Build AMD64 only for speed
    docker buildx build \
        --platform linux/amd64 \
        --file "$dockerfile" \
        --tag "$tag" \
        --push \
        --cache-from type=registry,ref=$tag \
        --cache-to type=inline \
        .
    
    if [ $? -eq 0 ]; then
        echo "✅ $service_name built and pushed successfully"
    else
        echo "❌ Failed to build $service_name"
        exit 1
    fi
}

# Build all services
for service in "${SERVICES[@]}"; do
    build_service "$service"
done

echo -e "\n✅ All services built and pushed (AMD64 only)"
echo -e "\nTo build multi-arch later, run:"
echo "./deployments/azure/build-multiarch.sh"