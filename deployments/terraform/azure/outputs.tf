output "resource_group_name" {
  value       = data.azurerm_resource_group.main.name
  description = "The name of the resource group"
}

output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "The name of the AKS cluster"
}

output "aks_cluster_id" {
  value       = azurerm_kubernetes_cluster.aks.id
  description = "The resource ID of the AKS cluster"
}

output "aks_kube_config" {
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
  description = "Raw Kubernetes config to be used with kubectl"
}

output "acr_login_server" {
  value       = data.azurerm_container_registry.acr.login_server
  description = "The login server URL for the container registry"
}

output "key_vault_name" {
  value       = azurerm_key_vault.main.name
  description = "The name of the Key Vault"
}

output "key_vault_uri" {
  value       = azurerm_key_vault.main.vault_uri
  description = "The URI of the Key Vault"
}

output "application_insights_instrumentation_key" {
  value       = var.enable_application_insights ? azurerm_application_insights.main[0].instrumentation_key : ""
  sensitive   = true
  description = "The instrumentation key for Application Insights"
}

output "application_insights_connection_string" {
  value       = var.enable_application_insights ? azurerm_application_insights.main[0].connection_string : ""
  sensitive   = true
  description = "The connection string for Application Insights"
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.main.workspace_id
  description = "The workspace ID of the Log Analytics workspace"
}

# Cloud service connection info
output "cloud_services" {
  value = {
    supabase_hint = "Using Supabase cloud database"
    qdrant_hint   = "Using Qdrant cloud vector database"
  }
  description = "Cloud services being used"
}

# Kubernetes connection command
output "kubectl_config_command" {
  value       = "az aks get-credentials --resource-group ${data.azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.aks.name}"
  description = "Command to configure kubectl"
}