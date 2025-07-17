# Azure Key Vault for secrets management

resource "azurerm_key_vault" "main" {
  name                        = "${var.project_name}-kv-${var.environment}"
  location                    = data.azurerm_resource_group.main.location
  resource_group_name         = data.azurerm_resource_group.main.name
  enabled_for_disk_encryption = false
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 90
  purge_protection_enabled    = true
  sku_name                   = "standard"
  
  # Enable RBAC authorization
  enable_rbac_authorization = true
  
  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
    
    virtual_network_subnet_ids = [azurerm_subnet.aks.id]
    
    # Add your IP for initial setup - remove in production
    ip_rules = ["31.54.115.247/32"]
  }
  
  tags = var.tags
}

# Key Vault Secrets
locals {
  secrets = {
    # Using cloud services - these are placeholder values
    "supabase-connection-string" = var.supabase_database_url
    "qdrant-cloud-url"          = var.qdrant_cloud_url
    "qdrant-api-key"            = var.qdrant_cloud_api_key
    "acr-login-server"          = data.azurerm_container_registry.acr.login_server
    "application-insights-key"   = var.enable_application_insights ? azurerm_application_insights.main[0].instrumentation_key : ""
  }
}

resource "azurerm_key_vault_secret" "secrets" {
  for_each = local.secrets
  
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.current_user_kv]
}

# Grant current user access to Key Vault for initial setup
resource "azurerm_role_assignment" "current_user_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Grant AKS access to Key Vault
resource "azurerm_role_assignment" "aks_kv_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

# Create AAD Pod Identity for Key Vault access
resource "azurerm_user_assigned_identity" "kvidentity" {
  name                = "${var.project_name}-kvidentity-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_role_assignment" "kvidentity_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.kvidentity.principal_id
}

# Kubernetes Secret Provider Class for Key Vault
# This will be created after AKS is deployed
# resource "kubernetes_manifest" "secretproviderclass" {
#   manifest = {
#     apiVersion = "secrets-store.csi.x-k8s.io/v1"
#     kind       = "SecretProviderClass"
#     metadata = {
#       name      = "azure-kvname"
#       namespace = kubernetes_namespace.qlp.metadata[0].name
#     }
#     spec = {
#       provider = "azure"
#       parameters = {
#         usePodIdentity         = "false"
#         useVMManagedIdentity   = "true"
#         userAssignedIdentityID = azurerm_user_assigned_identity.kvidentity.client_id
#         keyvaultName          = azurerm_key_vault.main.name
#         cloudName             = "AzurePublicCloud"
#         tenantId              = data.azurerm_client_config.current.tenant_id
#         
#         objects = jsonencode([
#           {
#             objectName = "postgres-connection-string"
#             objectType = "secret"
#           },
#           {
#             objectName = "redis-connection-string"
#             objectType = "secret"
#           },
#           {
#             objectName = "cosmos-connection-string"
#             objectType = "secret"
#           },
#           {
#             objectName = "storage-connection-string"
#             objectType = "secret"
#           },
#           {
#             objectName = "servicebus-connection-string"
#             objectType = "secret"
#           }
#         ])
#       }
#       
#       secretObjects = [
#         {
#           secretName = "qlp-azure-secrets"
#           type      = "Opaque"
#           data = [
#             {
#               objectName = "postgres-connection-string"
#               key        = "DATABASE_URL"
#             },
#             {
#               objectName = "redis-connection-string"
#               key        = "REDIS_URL"
#             },
#             {
#               objectName = "cosmos-connection-string"
#               key        = "COSMOS_CONNECTION_STRING"
#             },
#             {
#               objectName = "storage-connection-string"
#               key        = "STORAGE_CONNECTION_STRING"
#             },
#             {
#               objectName = "servicebus-connection-string"
#               key        = "SERVICEBUS_CONNECTION_STRING"
#             }
#           ]
#         }
#       ]
#     }
#   }
#   
#   depends_on = [
#     azurerm_kubernetes_cluster.aks,
#     kubernetes_namespace.qlp
#   ]
# }