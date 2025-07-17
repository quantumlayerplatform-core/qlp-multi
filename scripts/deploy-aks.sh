#!/bin/bash
set -e

# Azure Kubernetes Service (AKS) Deployment Script
# This script deploys the QLP platform to AKS using Terraform and kubectl

echo "🚀 Deploying Quantum Layer Platform to Azure Kubernetes Service (AKS)..."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_DIR="deployments/terraform/azure"
K8S_DIR="deployments/kubernetes/aks"
NAMESPACE="qlp-production"

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

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI not found. Please install it first."
        echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Please install it first."
        echo "Visit: https://www.terraform.io/downloads.html"
        exit 1
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install it first."
        echo "Visit: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install it first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    print_status "All prerequisites satisfied!"
}

# Login to Azure
azure_login() {
    print_status "Checking Azure login status..."
    
    if ! az account show &> /dev/null; then
        print_info "Not logged in to Azure. Initiating login..."
        az login
    else
        ACCOUNT=$(az account show --query name -o tsv)
        print_status "Already logged in to Azure account: $ACCOUNT"
    fi
}

# Initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    cd $TERRAFORM_DIR
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        print_warning "terraform.tfvars not found. Creating from example..."
        cp terraform.tfvars.example terraform.tfvars
        print_info "Please edit terraform.tfvars with your configuration before proceeding."
        exit 1
    fi
    
    # Initialize Terraform
    terraform init
    
    cd - > /dev/null
}

# Plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    cd $TERRAFORM_DIR
    
    terraform plan -out=tfplan
    
    echo ""
    read -p "Do you want to proceed with this plan? (yes/no): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled."
        exit 1
    fi
    
    cd - > /dev/null
}

# Apply Terraform deployment
apply_terraform() {
    print_status "Applying Terraform configuration..."
    cd $TERRAFORM_DIR
    
    terraform apply tfplan
    
    # Capture outputs
    ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
    AKS_CLUSTER_NAME=$(terraform output -raw aks_cluster_name)
    RESOURCE_GROUP=$(terraform output -raw resource_group_name)
    
    cd - > /dev/null
    
    print_status "Infrastructure deployed successfully!"
}

# Build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images to ACR..."
    
    # Login to ACR
    print_info "Logging in to ACR: $ACR_LOGIN_SERVER"
    az acr login --name ${ACR_LOGIN_SERVER%%.*}
    
    # Build multi-architecture images
    print_info "Building multi-architecture images..."
    ./scripts/build-multiarch.sh \
        --registry $ACR_LOGIN_SERVER \
        --tag latest \
        --push \
        --platforms linux/amd64,linux/arm64
    
    print_status "Docker images pushed successfully!"
}

# Configure kubectl
configure_kubectl() {
    print_status "Configuring kubectl for AKS..."
    
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP \
        --name $AKS_CLUSTER_NAME \
        --overwrite-existing
    
    # Verify connection
    kubectl cluster-info
    
    print_status "kubectl configured successfully!"
}

# Deploy Kubernetes resources
deploy_kubernetes() {
    print_status "Deploying Kubernetes resources..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets from .env file
    if [ -f ".env.production" ]; then
        print_info "Creating Kubernetes secrets from .env.production..."
        kubectl create secret generic qlp-secrets \
            --namespace=$NAMESPACE \
            --from-env-file=.env.production \
            --dry-run=client -o yaml | kubectl apply -f -
    else
        print_warning ".env.production not found. Please create secrets manually."
    fi
    
    # Replace placeholders in manifests
    export ACR_LOGIN_SERVER
    export IMAGE_TAG="latest"
    export AZURE_CLIENT_ID=$(az identity show \
        --name qlp-kvidentity-production \
        --resource-group $RESOURCE_GROUP \
        --query clientId -o tsv)
    
    # Apply manifests with environment substitution
    for manifest in $K8S_DIR/*.yaml; do
        print_info "Applying $(basename $manifest)..."
        envsubst < $manifest | kubectl apply -f -
    done
    
    print_status "Kubernetes resources deployed successfully!"
}

# Install NGINX Ingress Controller
install_ingress_controller() {
    print_status "Installing NGINX Ingress Controller..."
    
    # Add NGINX Helm repository
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    
    # Install NGINX Ingress Controller
    helm upgrade --install nginx-ingress ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.type=LoadBalancer \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --set controller.nodeSelector."workload"=qlp \
        --set controller.tolerations[0].key=workload \
        --set controller.tolerations[0].operator=Equal \
        --set controller.tolerations[0].value=qlp \
        --set controller.tolerations[0].effect=NoSchedule
    
    print_status "NGINX Ingress Controller installed!"
}

# Install cert-manager for TLS
install_cert_manager() {
    print_status "Installing cert-manager for TLS certificates..."
    
    # Add cert-manager Helm repository
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    
    # Install cert-manager
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --version v1.13.3 \
        --set installCRDs=true
    
    # Wait for cert-manager to be ready
    kubectl wait --namespace cert-manager \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/instance=cert-manager \
        --timeout=300s
    
    # Create ClusterIssuer for Let's Encrypt
    cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@yourcompany.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
    
    print_status "cert-manager installed!"
}

# Wait for deployments
wait_for_deployments() {
    print_status "Waiting for deployments to be ready..."
    
    # Wait for all deployments in namespace
    kubectl wait --namespace=$NAMESPACE \
        --for=condition=available \
        --timeout=600s \
        deployment --all
    
    print_status "All deployments are ready!"
}

# Display deployment information
display_info() {
    print_status "Deployment complete! Here's your deployment information:"
    
    echo ""
    echo "=== AKS Cluster Information ==="
    echo "Cluster Name: $AKS_CLUSTER_NAME"
    echo "Resource Group: $RESOURCE_GROUP"
    echo "ACR Login Server: $ACR_LOGIN_SERVER"
    
    echo ""
    echo "=== Service Status ==="
    kubectl get pods -n $NAMESPACE
    
    echo ""
    echo "=== Ingress Information ==="
    INGRESS_IP=$(kubectl get service nginx-ingress-controller \
        -n ingress-nginx \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending...")
    echo "Ingress IP: $INGRESS_IP"
    
    echo ""
    echo "=== Access Information ==="
    echo "API Endpoint: https://api.qlp.yourdomain.com"
    echo "Health Check: https://health.qlp.yourdomain.com"
    echo "Grafana: https://grafana.qlp.yourdomain.com"
    echo "Jaeger: https://jaeger.qlp.yourdomain.com"
    echo "Temporal UI: http://$INGRESS_IP:8088"
    
    echo ""
    echo "=== Next Steps ==="
    echo "1. Update your DNS records to point to: $INGRESS_IP"
    echo "2. Update the ingress hosts in $K8S_DIR/ingress.yaml"
    echo "3. Monitor the deployment: kubectl logs -f -n $NAMESPACE -l app=orchestrator"
    echo "4. Access Grafana for monitoring (admin password in Key Vault)"
    
    echo ""
    print_status "🎉 QLP successfully deployed to AKS!"
}

# Main deployment flow
main() {
    print_status "Starting QLP AKS deployment..."
    
    check_prerequisites
    azure_login
    
    # Terraform deployment
    if [ "$1" != "--skip-terraform" ]; then
        init_terraform
        plan_terraform
        apply_terraform
    else
        print_warning "Skipping Terraform deployment..."
        # Get values from existing deployment
        cd $TERRAFORM_DIR
        ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
        AKS_CLUSTER_NAME=$(terraform output -raw aks_cluster_name)
        RESOURCE_GROUP=$(terraform output -raw resource_group_name)
        cd - > /dev/null
    fi
    
    # Build and push images
    if [ "$1" != "--skip-build" ]; then
        build_and_push_images
    else
        print_warning "Skipping Docker build..."
    fi
    
    # Kubernetes deployment
    configure_kubectl
    deploy_kubernetes
    install_ingress_controller
    install_cert_manager
    wait_for_deployments
    display_info
}

# Run main function
main "$@"