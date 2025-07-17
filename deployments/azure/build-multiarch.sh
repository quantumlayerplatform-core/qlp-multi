#!/bin/bash
set -euo pipefail

# Azure Container Registry Configuration
# These need to be set before running the script
: ${ACR_NAME:="qlpregistry"}
: ${RESOURCE_GROUP:="qlp-rg"}
: ${LOCATION:="uksouth"}
: ${AZURE_SUBSCRIPTION_ID:=""}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== QLP Multi-Architecture Build & Push Script ===${NC}"
echo "Building for AMD64 and ARM64 architectures"

# Check if required tools are installed
check_requirements() {
    local missing_tools=()
    
    # Check for required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v az >/dev/null 2>&1 || missing_tools+=("az (Azure CLI)")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required tools: ${missing_tools[*]}${NC}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check if Docker buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker buildx not found. Installing...${NC}"
        docker buildx install
    fi
}

# Login to Azure and ACR
setup_azure() {
    echo -e "\n${YELLOW}Setting up Azure connection...${NC}"
    
    # Check if already logged in
    if ! az account show >/dev/null 2>&1; then
        echo "Please login to Azure:"
        az login
    fi
    
    # Set subscription if provided
    if [ -n "$AZURE_SUBSCRIPTION_ID" ]; then
        az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    fi
    
    # Create resource group if it doesn't exist
    if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
        echo -e "${YELLOW}Creating resource group $RESOURCE_GROUP in $LOCATION...${NC}"
        az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    fi
    
    # Create ACR if it doesn't exist
    if ! az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
        echo -e "${YELLOW}Creating Azure Container Registry $ACR_NAME...${NC}"
        az acr create --resource-group "$RESOURCE_GROUP" \
            --name "$ACR_NAME" \
            --sku Standard \
            --location "$LOCATION"
    fi
    
    # Login to ACR
    echo -e "${YELLOW}Logging in to Azure Container Registry...${NC}"
    az acr login --name "$ACR_NAME"
    
    # Get ACR login server
    ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
    echo -e "${GREEN}ACR Login Server: $ACR_LOGIN_SERVER${NC}"
}

# Create or use existing buildx builder
setup_buildx() {
    echo -e "\n${YELLOW}Setting up Docker buildx for multi-arch builds...${NC}"
    
    # Check if our builder exists
    if ! docker buildx ls | grep -q "qlp-builder"; then
        echo "Creating new buildx builder..."
        docker buildx create --name qlp-builder --driver docker-container --use
    else
        echo "Using existing qlp-builder"
        docker buildx use qlp-builder
    fi
    
    # Bootstrap the builder
    docker buildx inspect --bootstrap
}

# Build and push multi-architecture image
build_and_push() {
    local service_name=$1
    local dockerfile_path=$2
    local context_path=${3:-.}
    
    echo -e "\n${YELLOW}Building $service_name for multiple architectures...${NC}"
    
    # Construct the full image tag
    local image_tag="${ACR_LOGIN_SERVER}/qlp/${service_name}:latest"
    
    # Build and push multi-arch image
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --file "$dockerfile_path" \
        --tag "$image_tag" \
        --push \
        "$context_path"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully built and pushed $service_name${NC}"
    else
        echo -e "${RED}✗ Failed to build $service_name${NC}"
        exit 1
    fi
}

# Main execution
main() {
    check_requirements
    setup_azure
    setup_buildx
    
    echo -e "\n${GREEN}Starting multi-architecture builds...${NC}"
    
    # Build all services
    build_and_push "orchestrator" "services/orchestrator/Dockerfile" "."
    build_and_push "agent-factory" "services/agents/Dockerfile" "."
    build_and_push "validation-mesh" "services/validation/Dockerfile" "."
    build_and_push "vector-memory" "services/memory/Dockerfile" "."
    build_and_push "execution-sandbox" "services/sandbox/Dockerfile" "."
    build_and_push "temporal-worker" "deployments/docker/Dockerfile.temporal-worker" "."
    build_and_push "marketing-worker" "services/marketing/Dockerfile" "."
    
    # Also build supporting images if they have custom Dockerfiles
    if [ -f "deployments/nginx/Dockerfile" ]; then
        build_and_push "nginx" "deployments/nginx/Dockerfile" "."
    fi
    
    echo -e "\n${GREEN}=== All images built and pushed successfully! ===${NC}"
    echo -e "Images are available at: ${ACR_LOGIN_SERVER}/qlp/*"
    echo -e "\nNext steps:"
    echo -e "1. Update Kubernetes manifests with the new image URLs"
    echo -e "2. Deploy to AKS using: ./deploy-to-aks.sh"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --acr-name)
            ACR_NAME="$2"
            shift 2
            ;;
        --resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --subscription)
            AZURE_SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --acr-name        Name of the Azure Container Registry (default: qlpregistry)"
            echo "  --resource-group  Name of the resource group (default: qlp-rg)"
            echo "  --location        Azure region (default: uksouth)"
            echo "  --subscription    Azure subscription ID"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main