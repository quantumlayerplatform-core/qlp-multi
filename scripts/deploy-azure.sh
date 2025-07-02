#!/bin/bash
set -e

# Azure deployment script for QLP

echo "☁️  Deploying Quantum Layer Platform to Azure..."

# Configuration
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-qlp-production}"
LOCATION="${AZURE_LOCATION:-eastus}"
ACR_NAME="${AZURE_ACR_NAME:-qlpregistry}"
AKS_CLUSTER="${AZURE_AKS_CLUSTER:-qlp-cluster}"
COSMOS_ACCOUNT="${AZURE_COSMOS_ACCOUNT:-qlp-cosmos}"
STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT:-qlpstorage}"

# Check Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install it first."
    exit 1
fi

# Login to Azure
echo "🔐 Logging in to Azure..."
az login

# Create resource group
echo "📁 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
echo "🏗️  Creating Azure Container Registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Standard \
    --admin-enabled true

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Login to ACR
echo "🔐 Logging in to ACR..."
docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD

# Build and push images
echo "🐳 Building and pushing Docker images..."
./scripts/docker-build.sh --push --registry $ACR_LOGIN_SERVER --tag latest

# Create AKS cluster
echo "🎯 Creating AKS cluster..."
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_CLUSTER \
    --node-count 3 \
    --node-vm-size Standard_D4s_v3 \
    --enable-addons monitoring \
    --generate-ssh-keys \
    --attach-acr $ACR_NAME

# Get AKS credentials
echo "📥 Getting AKS credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER

# Create Cosmos DB (PostgreSQL)
echo "🗄️  Creating Azure Database for PostgreSQL..."
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name qlp-postgres \
    --location $LOCATION \
    --admin-user qlpadmin \
    --admin-password "QLPSecurePass123!" \
    --sku-name Standard_D2s_v3 \
    --version 15

# Create Storage Account
echo "💾 Creating Storage Account..."
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2

# Get storage connection string
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query connectionString -o tsv)

# Create Kubernetes namespace
echo "📦 Creating Kubernetes namespace..."
kubectl create namespace qlp-production || true

# Create Kubernetes secrets
echo "🔐 Creating Kubernetes secrets..."
kubectl create secret generic qlp-secrets \
    --namespace=qlp-production \
    --from-literal=AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    --from-literal=AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONNECTION_STRING" \
    --from-literal=POSTGRES_PASSWORD="QLPSecurePass123!" \
    || kubectl patch secret qlp-secrets \
        --namespace=qlp-production \
        -p "{\"data\":{\"AZURE_OPENAI_API_KEY\":\"$(echo -n $AZURE_OPENAI_API_KEY | base64)\"}}"

# Deploy to Kubernetes
echo "🚀 Deploying to Kubernetes..."
kubectl apply -f k8s/ --namespace=qlp-production

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --namespace=qlp-production \
    --for=condition=ready pod \
    --selector=app=qlp-orchestrator \
    --timeout=300s

# Get external IP
echo "🌐 Getting external IP..."
EXTERNAL_IP=$(kubectl get service qlp-nginx \
    --namespace=qlp-production \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Platform URL: http://$EXTERNAL_IP"
echo "📊 Kubernetes Dashboard: az aks browse --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER"
echo "📝 Logs: kubectl logs -f deployment/qlp-orchestrator --namespace=qlp-production"
echo ""
echo "🔧 To scale the deployment:"
echo "  kubectl scale deployment qlp-agent-factory --replicas=5 --namespace=qlp-production"