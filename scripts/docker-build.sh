#!/bin/bash
set -e

# Build script for QLP Docker images

echo "🐳 Building Quantum Layer Platform Docker Images..."

# Load environment variables
if [ -f .env.docker ]; then
    export $(cat .env.docker | grep -v '^#' | xargs)
fi

# Parse command line arguments
BUILD_PUSH=false
REGISTRY=""
TAG="latest"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --push) BUILD_PUSH=true ;;
        --registry) REGISTRY="$2"; shift ;;
        --tag) TAG="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Build the main QLP image
echo "📦 Building main QLP image..."
docker build -t qlp-platform:${TAG} -f Dockerfile .

# Tag for registry if specified
if [ ! -z "$REGISTRY" ]; then
    docker tag qlp-platform:${TAG} ${REGISTRY}/qlp-platform:${TAG}
fi

# Build individual service images (optional)
echo "📦 Building service-specific images..."
for service in orchestrator agent-factory validation-mesh vector-memory execution-sandbox; do
    echo "  Building ${service}..."
    docker build \
        --build-arg SERVICE_NAME=${service} \
        -t qlp-${service}:${TAG} \
        -f Dockerfile .
    
    if [ ! -z "$REGISTRY" ]; then
        docker tag qlp-${service}:${TAG} ${REGISTRY}/qlp-${service}:${TAG}
    fi
done

# Push images if requested
if [ "$BUILD_PUSH" = true ] && [ ! -z "$REGISTRY" ]; then
    echo "🚀 Pushing images to registry..."
    docker push ${REGISTRY}/qlp-platform:${TAG}
    
    for service in orchestrator agent-factory validation-mesh vector-memory execution-sandbox; do
        docker push ${REGISTRY}/qlp-${service}:${TAG}
    done
fi

echo "✅ Build complete!"
echo ""
echo "To run the platform locally:"
echo "  docker-compose -f docker-compose.platform.yml up"
echo ""
echo "To deploy to Azure:"
echo "  ./scripts/deploy-azure.sh"