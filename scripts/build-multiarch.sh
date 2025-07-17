#!/bin/bash
set -e

# Multi-architecture Docker build script for Azure Container Registry
# Supports both AMD64 and ARM64 architectures

echo "🏗️  Building multi-architecture Docker images for QLP..."

# Configuration
REGISTRY="${REGISTRY:-}"
TAG="${TAG:-latest}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
PUSH="${PUSH:-false}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Services to build
SERVICES=(
    "orchestrator"
    "agent-factory"
    "validation-mesh"
    "vector-memory"
    "execution-sandbox"
    "temporal-worker"
)

# Function to print colored output
print_status() {
    echo -e "${GREEN}▶${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if Docker buildx is available
if ! docker buildx version &> /dev/null; then
    print_error "Docker buildx not found. Please update Docker Desktop or install buildx plugin."
    exit 1
fi

# Create or use existing buildx builder
BUILDER_NAME="qlp-multiarch-builder"
if ! docker buildx inspect $BUILDER_NAME &> /dev/null; then
    print_status "Creating new buildx builder: $BUILDER_NAME"
    docker buildx create --name $BUILDER_NAME --use --platform=$PLATFORMS
else
    print_status "Using existing buildx builder: $BUILDER_NAME"
    docker buildx use $BUILDER_NAME
fi

# Start the builder
docker buildx inspect --bootstrap

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --push)
            PUSH="true"
            shift
            ;;
        --platforms)
            PLATFORMS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--registry REGISTRY] [--tag TAG] [--push] [--platforms PLATFORMS]"
            exit 1
            ;;
    esac
done

# Validate registry if push is enabled
if [ "$PUSH" == "true" ] && [ -z "$REGISTRY" ]; then
    print_error "Registry must be specified when using --push"
    exit 1
fi

# Build base image first
print_status "Building base image..."
IMAGE_NAME="qlp-base"
FULL_IMAGE_NAME="${REGISTRY:+${REGISTRY}/}${IMAGE_NAME}:${TAG}"

BUILD_ARGS="--platform=$PLATFORMS"
if [ "$PUSH" == "true" ]; then
    BUILD_ARGS="$BUILD_ARGS --push"
else
    BUILD_ARGS="$BUILD_ARGS --load"
fi

docker buildx build \
    $BUILD_ARGS \
    -f Dockerfile.base \
    -t "$FULL_IMAGE_NAME" \
    --cache-from=type=registry,ref=$FULL_IMAGE_NAME \
    --cache-to=type=inline \
    .

# Build service images
for SERVICE in "${SERVICES[@]}"; do
    print_status "Building $SERVICE..."
    
    # Determine Dockerfile path and context
    case $SERVICE in
        "orchestrator")
            DOCKERFILE="services/orchestrator/Dockerfile"
            CONTEXT="."
            IMAGE_NAME="qlp-orchestrator"
            ;;
        "agent-factory")
            DOCKERFILE="services/agents/Dockerfile"
            CONTEXT="."
            IMAGE_NAME="qlp-agent-factory"
            ;;
        "validation-mesh")
            DOCKERFILE="services/validation/Dockerfile"
            CONTEXT="."
            IMAGE_NAME="qlp-validation-mesh"
            ;;
        "vector-memory")
            DOCKERFILE="services/memory/Dockerfile"
            CONTEXT="."
            IMAGE_NAME="qlp-vector-memory"
            ;;
        "execution-sandbox")
            DOCKERFILE="services/sandbox/Dockerfile"
            CONTEXT="."
            IMAGE_NAME="qlp-execution-sandbox"
            ;;
        "temporal-worker")
            DOCKERFILE="deployments/docker/Dockerfile.temporal-worker"
            CONTEXT="."
            IMAGE_NAME="qlp-temporal-worker"
            ;;
    esac
    
    # Check if Dockerfile exists
    if [ ! -f "$DOCKERFILE" ]; then
        print_warning "Dockerfile not found: $DOCKERFILE, skipping $SERVICE"
        continue
    fi
    
    FULL_IMAGE_NAME="${REGISTRY:+${REGISTRY}/}${IMAGE_NAME}:${TAG}"
    
    # Build with buildx for multi-architecture
    docker buildx build \
        $BUILD_ARGS \
        -f "$DOCKERFILE" \
        -t "$FULL_IMAGE_NAME" \
        --build-arg BASE_IMAGE="${REGISTRY:+${REGISTRY}/}qlp-base:${TAG}" \
        --cache-from=type=registry,ref=$FULL_IMAGE_NAME \
        --cache-to=type=inline \
        "$CONTEXT"
    
    if [ $? -eq 0 ]; then
        print_status "✓ Successfully built $SERVICE"
    else
        print_error "Failed to build $SERVICE"
        exit 1
    fi
done

# Build additional images if they exist
ADDITIONAL_IMAGES=(
    "hap:services/hap/Dockerfile:qlp-hap"
)

for ENTRY in "${ADDITIONAL_IMAGES[@]}"; do
    IFS=':' read -r SERVICE DOCKERFILE IMAGE_NAME <<< "$ENTRY"
    
    if [ -f "$DOCKERFILE" ]; then
        print_status "Building additional image: $SERVICE..."
        FULL_IMAGE_NAME="${REGISTRY:+${REGISTRY}/}${IMAGE_NAME}:${TAG}"
        
        docker buildx build \
            $BUILD_ARGS \
            -f "$DOCKERFILE" \
            -t "$FULL_IMAGE_NAME" \
            --cache-from=type=registry,ref=$FULL_IMAGE_NAME \
            --cache-to=type=inline \
            .
    fi
done

print_status "🎉 Multi-architecture build complete!"

# Show built images
if [ "$PUSH" != "true" ]; then
    print_status "Built images (local only):"
    docker images | grep -E "qlp-|REPOSITORY" | head -n 20
else
    print_status "Images pushed to registry: $REGISTRY"
    print_status "To use these images, update your Kubernetes manifests with:"
    echo "  image: $REGISTRY/<service-name>:$TAG"
fi

# Provide next steps
echo ""
print_status "Next steps:"
echo "  1. To push to ACR: ./scripts/build-multiarch.sh --registry <acr-name>.azurecr.io --tag latest --push"
echo "  2. To build specific platforms: ./scripts/build-multiarch.sh --platforms linux/amd64"
echo "  3. To test locally: docker run --platform linux/arm64 <image-name>"