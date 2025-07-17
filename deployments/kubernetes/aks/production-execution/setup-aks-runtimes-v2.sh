#!/bin/bash
# Production setup for multiple container runtimes in AKS with proper subnet

RESOURCE_GROUP="qlp-rg"
CLUSTER_NAME="qlp-aks-production"
VNET_NAME="qlp-vnet-production"
SUBNET_NAME="aks-runtime-subnet"

# Get subnet ID
SUBNET_ID=$(az network vnet subnet show \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --query id -o tsv)

echo "=== Configuring AKS for Production Container Runtimes ==="
echo "Using subnet: $SUBNET_ID"

# Create a node pool for gVisor (most common for untrusted code)
echo "Creating gVisor node pool..."
az aks nodepool add \
  --resource-group $RESOURCE_GROUP \
  --cluster-name $CLUSTER_NAME \
  --name gvisornodes \
  --node-count 2 \
  --node-vm-size Standard_D4s_v3 \
  --vnet-subnet-id $SUBNET_ID \
  --node-taints runtime=gvisor:NoSchedule \
  --labels runtime=gvisor \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5 \
  --max-pods 110

# Create a node pool with nested virtualization for Kata Containers
echo "Creating Kata Containers node pool..."
az aks nodepool add \
  --resource-group $RESOURCE_GROUP \
  --cluster-name $CLUSTER_NAME \
  --name katanodes \
  --node-count 1 \
  --node-vm-size Standard_D8s_v4 \
  --vnet-subnet-id $SUBNET_ID \
  --node-taints runtime=kata:NoSchedule \
  --labels runtime=kata \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 3 \
  --max-pods 50

# Create a high-performance node pool for native execution
echo "Creating high-performance native execution node pool..."
az aks nodepool add \
  --resource-group $RESOURCE_GROUP \
  --cluster-name $CLUSTER_NAME \
  --name fastnodes \
  --node-count 2 \
  --node-vm-size Standard_F4s_v2 \
  --vnet-subnet-id $SUBNET_ID \
  --node-taints runtime=native:NoSchedule \
  --labels runtime=native \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 10 \
  --max-pods 250

echo "Node pools created successfully!"

# Install runtime classes
echo "Installing runtime classes..."
kubectl apply -f runtime-classes.yaml

echo "Production runtime setup complete!"