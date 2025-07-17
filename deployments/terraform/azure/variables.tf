variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
  default     = "qlp-production"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "uksouth"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "qlp"
}

# AKS Configuration
variable "aks_node_count" {
  description = "Initial number of nodes for AKS cluster"
  type        = number
  default     = 3
}

variable "aks_min_nodes" {
  description = "Minimum number of nodes for autoscaling"
  type        = number
  default     = 3
}

variable "aks_max_nodes" {
  description = "Maximum number of nodes for autoscaling"
  type        = number
  default     = 10
}

variable "aks_node_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29.2"
}

# Database Configuration
variable "postgres_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "qlpadmin"
}

variable "postgres_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
  default     = ""  # Not used - using cloud services
}

variable "postgres_sku" {
  description = "PostgreSQL SKU"
  type        = string
  default     = "GP_Standard_D2s_v3"
}

# Cosmos DB Configuration
variable "cosmos_consistency_level" {
  description = "Cosmos DB consistency level"
  type        = string
  default     = "Session"
}

# Service Bus Configuration
variable "service_bus_sku" {
  description = "Service Bus SKU"
  type        = string
  default     = "Standard"
}

# Application Insights
variable "enable_application_insights" {
  description = "Enable Application Insights"
  type        = bool
  default     = true
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "QuantumLayerPlatform"
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}

# GitHub token for ACR Tasks
variable "github_token" {
  description = "GitHub token for ACR build tasks"
  type        = string
  sensitive   = true
  default     = ""
}

# Cloud service URLs
variable "supabase_database_url" {
  description = "Supabase PostgreSQL connection string"
  type        = string
  sensitive   = true
  default     = ""
}

variable "qdrant_cloud_url" {
  description = "Qdrant Cloud URL"
  type        = string
  default     = ""
}

variable "qdrant_cloud_api_key" {
  description = "Qdrant Cloud API key"
  type        = string
  sensitive   = true
  default     = ""
}