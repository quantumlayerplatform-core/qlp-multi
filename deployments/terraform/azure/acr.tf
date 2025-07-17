# Azure Container Registry (ACR) - Using existing ACR

data "azurerm_container_registry" "acr" {
  name                = "qlpregistry"
  resource_group_name = data.azurerm_resource_group.main.name
}

# ACR Tasks and webhooks commented out for now - can be added later
# # ACR Tasks for automated multi-arch builds
# resource "azurerm_container_registry_task" "multiarch_build" {
#   for_each = toset([
#     "orchestrator",
#     "agent-factory",
#     "validation-mesh",
#     "vector-memory",
#     "execution-sandbox",
#     "temporal-worker"
#   ])
#   
#   name                  = "build-${each.key}"
#   container_registry_id = data.azurerm_container_registry.acr.id
#   
#   platform {
#     os           = "Linux"
#     architecture = "amd64"
#   }
#   
#   docker_step {
#     dockerfile_path = lookup({
#       "orchestrator"      = "services/orchestrator/Dockerfile",
#       "agent-factory"     = "services/agents/Dockerfile",
#       "validation-mesh"   = "services/validation/Dockerfile",
#       "vector-memory"     = "services/memory/Dockerfile",
#       "execution-sandbox" = "services/sandbox/Dockerfile",
#       "temporal-worker"   = "deployments/docker/Dockerfile.temporal-worker"
#     }, each.key, "Dockerfile")
#     
#     context_path         = "https://github.com/quantumlayer/qlp-dev.git"
#     context_access_token = var.github_token
#     image_names          = ["qlp-${each.key}:{{.Run.ID}}"]
#     
#   }
#   
#   agent_setting {
#     cpu = 2
#   }
#   
#   timeout_in_seconds = 3600
#   
#   base_image_trigger {
#     name                        = "defaultBaseimageTriggerName"
#     type                        = "Runtime"
#     enabled                     = true
#     update_trigger_payload_type = "Default"
#   }
#   
#   tags = var.tags
# }
# 
# # ACR Webhook for automated deployments
# resource "azurerm_container_registry_webhook" "aks_deploy" {
#   name                = "aksdeploywebhook"
#   registry_name       = data.azurerm_container_registry.acr.name
#   resource_group_name = data.azurerm_resource_group.main.name
#   location            = data.azurerm_resource_group.main.location
#   
#   service_uri = "https://your-webhook-endpoint.com/deploy"  # Replace with actual webhook
#   status      = "enabled"
#   scope       = "qlp-*:*"
#   
#   actions = [
#     "push"
#   ]
#   
#   custom_headers = {
#     "Content-Type" = "application/json"
#   }
# }

# ACR login server output moved to outputs.tf