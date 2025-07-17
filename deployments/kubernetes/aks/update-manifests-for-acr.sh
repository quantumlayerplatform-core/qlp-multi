#!/bin/bash
# Update all Kubernetes manifests to use Azure Container Registry images

set -e

ACR_REGISTRY="qlpregistry.azurecr.io"
OLD_REGISTRY="satishgoda"

echo "========================================"
echo "Updating Kubernetes manifests for ACR"
echo "From: $OLD_REGISTRY"
echo "To: $ACR_REGISTRY"
echo "========================================"

# Function to update image references in YAML files
update_manifest() {
    local file=$1
    if [[ -f "$file" ]]; then
        echo "Updating: $file"
        sed -i.bak "s|image: $OLD_REGISTRY/|image: $ACR_REGISTRY/|g" "$file"
        # Also update any fully qualified image references
        sed -i.bak "s|image: docker.io/$OLD_REGISTRY/|image: $ACR_REGISTRY/|g" "$file"
    fi
}

# Update all deployment files
echo "Updating deployment manifests..."
find deployments/kubernetes -name "*.yaml" -o -name "*.yml" | while read -r file; do
    update_manifest "$file"
done

# Clean up backup files
echo "Cleaning up backup files..."
find deployments/kubernetes -name "*.bak" -delete

echo ""
echo "========================================"
echo "Update Complete!"
echo "========================================"
echo ""
echo "Manifests have been updated to use ACR images."
echo ""
echo "Next steps:"
echo "1. Build and push images: ./build-and-push-azure-multiarch.sh"
echo "2. Deploy to AKS: cd deployments/kubernetes/aks/temporal-cloud && ./deploy-temporal-cloud.sh"