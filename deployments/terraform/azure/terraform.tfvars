# QLP Azure Infrastructure Configuration

# Use existing resource group
resource_group_name = "qlp-rg"
location           = "uksouth"
environment        = "production"
project_name       = "qlp"

# AKS Configuration - Start small for testing
aks_node_count = 2
aks_min_nodes  = 2
aks_max_nodes  = 5
aks_node_size  = "Standard_D2s_v3"  # Smaller size for initial deployment

# Kubernetes version (check available versions with: az aks get-versions --location uksouth)
kubernetes_version = "1.30.12"

# Database - Using cloud services instead
# postgres_admin_username = "qlpadmin"
# postgres_admin_password = "ChangeMeInProduction123!"

# Cloud service URLs
supabase_database_url = "postgresql://postgres:nwGE5hunfncm57NU@db.piqrwahqrxuyfnzfoosq.supabase.co:5432/postgres"
qdrant_cloud_url      = "https://f12abb28-83ff-4395-aaff-ad75227bf36f.eu-west-2-0.aws.cloud.qdrant.io:6333"
qdrant_cloud_api_key  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.HnvLOfRB9mK0THYZPF0PlqHnKZ8fOc2U6L6aEI4T5QQ"

# Tags
tags = {
  Project     = "QuantumLayerPlatform"
  Environment = "Production"
  ManagedBy   = "Terraform"
  CreatedBy   = "satishgs@outlook.com"
}