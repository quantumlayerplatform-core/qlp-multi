terraform {
  required_version = ">= 1.3.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12.0"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "qlp-terraform-state"
    storage_account_name = "qlptfstate820f83"
    container_name       = "tfstate"
    key                  = "qlp-production.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  skip_provider_registration = true
}

provider "kubernetes" {
  host                   = try(azurerm_kubernetes_cluster.aks.kube_config.0.host, "")
  client_certificate     = try(base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_certificate), "")
  client_key             = try(base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_key), "")
  cluster_ca_certificate = try(base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.cluster_ca_certificate), "")
}

provider "helm" {
  kubernetes {
    host                   = try(azurerm_kubernetes_cluster.aks.kube_config.0.host, "")
    client_certificate     = try(base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_certificate), "")
    client_key             = try(base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_key), "")
    cluster_ca_certificate = try(base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.cluster_ca_certificate), "")
  }
}

# Data source for current subscription
data "azurerm_client_config" "current" {}

# Use existing Resource Group
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  count               = var.enable_application_insights ? 1 : 0
  name                = "${var.project_name}-appinsights-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = var.tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet-${var.environment}"
  address_space       = ["10.0.0.0/16"]
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = var.tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = data.azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
  
  service_endpoints = ["Microsoft.KeyVault", "Microsoft.Storage"]
}

# Subnet for Azure services
resource "azurerm_subnet" "services" {
  name                 = "services-subnet"
  resource_group_name  = data.azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
  
  delegation {
    name = "postgres-delegation"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Network Security Group for AKS
resource "azurerm_network_security_group" "aks" {
  name                = "${var.project_name}-aks-nsg-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}