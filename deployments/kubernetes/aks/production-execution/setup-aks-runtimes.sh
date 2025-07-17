#!/bin/bash
# Production setup for multiple container runtimes in AKS

# Enable containerd and configure for multiple runtimes
echo "=== Configuring AKS for Production Container Runtimes ==="

# 1. Create specialized node pools for different runtimes
echo "Creating specialized node pools..."

# Standard node pool (already exists)
# Uses default containerd runtime

# Create a node pool with nested virtualization for Kata Containers
az aks nodepool add \
  --resource-group qlp-rg \
  --cluster-name qlp-aks-production \
  --name katanodes \
  --node-count 2 \
  --node-vm-size Standard_D4s_v4 \
  --node-taints runtime=kata:NoSchedule \
  --labels runtime=kata \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5

# Create a node pool for gVisor
az aks nodepool add \
  --resource-group qlp-rg \
  --cluster-name qlp-aks-production \
  --name gvisornodes \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --node-taints runtime=gvisor:NoSchedule \
  --labels runtime=gvisor \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5

# Create a node pool for Firecracker (requires bare metal or nested virt)
az aks nodepool add \
  --resource-group qlp-rg \
  --cluster-name qlp-aks-production \
  --name fcnodes \
  --node-count 1 \
  --node-vm-size Standard_D8s_v4 \
  --node-taints runtime=firecracker:NoSchedule \
  --labels runtime=firecracker \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 3

echo "Node pools created successfully!"