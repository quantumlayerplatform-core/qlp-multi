# Azure Kubernetes Service (AKS) Cluster

# User Assigned Identity for AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${var.project_name}-aks-identity-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = var.tags
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${var.project_name}-aks-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-${var.environment}"
  kubernetes_version  = var.kubernetes_version
  
  default_node_pool {
    name                 = "system"
    node_count           = 2
    vm_size              = "Standard_D2s_v3"
    os_disk_size_gb      = 100
    vnet_subnet_id       = azurerm_subnet.aks.id
    enable_auto_scaling  = true
    min_count            = 2
    max_count            = 4
    max_pods             = 110
    zones                = ["1", "2", "3"]
    enable_node_public_ip = false
    
    upgrade_settings {
      max_surge = "33%"
    }
    
    tags = var.tags
  }
  
  # Additional node pool for workloads
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }
  
  network_profile {
    network_plugin     = "azure"
    network_policy     = "calico"
    dns_service_ip     = "10.2.0.10"
    service_cidr       = "10.2.0.0/24"
    load_balancer_sku  = "standard"
  }
  
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }
  
  azure_policy_enabled = true
  
  auto_scaler_profile {
    balance_similar_node_groups      = true
    expander                        = "random"
    max_graceful_termination_sec    = 600
    max_unready_nodes               = 3
    new_pod_scale_up_delay          = "10s"
    scale_down_delay_after_add      = "10m"
    scale_down_delay_after_delete   = "10s"
    scale_down_delay_after_failure  = "3m"
    scan_interval                   = "10s"
    scale_down_unneeded             = "10m"
    scale_down_unready              = "20m"
    scale_down_utilization_threshold = 0.5
  }
  
  maintenance_window {
    allowed {
      day   = "Sunday"
      hours = [2, 6]
    }
  }
  
  tags = var.tags
}

# Additional Node Pool for QLP Workloads
resource "azurerm_kubernetes_cluster_node_pool" "workload" {
  name                  = "workload"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size              = var.aks_node_size
  node_count           = var.aks_node_count
  vnet_subnet_id       = azurerm_subnet.aks.id
  
  enable_auto_scaling   = true
  min_count            = var.aks_min_nodes
  max_count            = var.aks_max_nodes
  max_pods             = 110
  zones                = ["1", "2", "3"]
  enable_node_public_ip = false
  os_disk_size_gb      = 100
  
  node_labels = {
    "workload" = "qlp"
    "tier"     = "application"
  }
  
  node_taints = [
    "workload=qlp:NoSchedule"
  ]
  
  upgrade_settings {
    max_surge = "33%"
  }
  
  tags = var.tags
}

# Grant AKS cluster access to ACR
resource "azurerm_role_assignment" "aks_acr" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                           = data.azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# Grant AKS managed identity Network Contributor on subnet
resource "azurerm_role_assignment" "aks_subnet" {
  scope                = azurerm_subnet.aks.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# Kubernetes Namespace for QLP
resource "kubernetes_namespace" "qlp" {
  metadata {
    name = "qlp-production"
    
    labels = {
      environment = var.environment
      managed-by  = "terraform"
    }
  }
  
  depends_on = [azurerm_kubernetes_cluster.aks]
}