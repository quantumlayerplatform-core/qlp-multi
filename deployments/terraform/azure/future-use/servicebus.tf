# Azure Service Bus for message queuing

resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.project_name}-servicebus-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.service_bus_sku
  capacity            = var.service_bus_sku == "Premium" ? 1 : 0
  
  # Enable zone redundancy for Premium tier
  zone_redundant = var.service_bus_sku == "Premium" ? true : false
  
  tags = var.tags
}

# Service Bus Queue for agent tasks
resource "azurerm_servicebus_queue" "agent_tasks" {
  name         = "agent-tasks"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  enable_partitioning                  = true
  max_size_in_megabytes               = 5120
  lock_duration                       = "PT5M"
  max_delivery_count                  = 10
  default_message_ttl                 = "P14D"
  duplicate_detection_history_time_window = "PT10M"
  enable_batched_operations           = true
  requires_duplicate_detection        = true
  requires_session                    = false
  dead_lettering_on_message_expiration = true
}

# Service Bus Queue for validation tasks
resource "azurerm_servicebus_queue" "validation_tasks" {
  name         = "validation-tasks"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  enable_partitioning                  = true
  max_size_in_megabytes               = 5120
  lock_duration                       = "PT3M"
  max_delivery_count                  = 5
  default_message_ttl                 = "P7D"
  duplicate_detection_history_time_window = "PT10M"
  enable_batched_operations           = true
  requires_duplicate_detection        = true
  requires_session                    = false
  dead_lettering_on_message_expiration = true
}

# Service Bus Topic for event broadcasting
resource "azurerm_servicebus_topic" "events" {
  name         = "platform-events"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  enable_partitioning                  = true
  max_size_in_megabytes               = 5120
  default_message_ttl                 = "P1D"
  duplicate_detection_history_time_window = "PT10M"
  enable_batched_operations           = true
  requires_duplicate_detection        = true
  support_ordering                    = true
}

# Subscription for workflow events
resource "azurerm_servicebus_subscription" "workflow_events" {
  name               = "workflow-events"
  topic_id           = azurerm_servicebus_topic.events.id
  max_delivery_count = 10
  
  default_message_ttl                 = "P1D"
  lock_duration                       = "PT1M"
  dead_lettering_on_message_expiration = true
  enable_batched_operations           = true
  requires_session                    = false
}

# Subscription for capsule events
resource "azurerm_servicebus_subscription" "capsule_events" {
  name               = "capsule-events"
  topic_id           = azurerm_servicebus_topic.events.id
  max_delivery_count = 10
  
  default_message_ttl                 = "P7D"
  lock_duration                       = "PT1M"
  dead_lettering_on_message_expiration = true
  enable_batched_operations           = true
  requires_session                    = false
}

# Service Bus Authorization Rules
resource "azurerm_servicebus_namespace_authorization_rule" "qlp_services" {
  name         = "qlp-services-rule"
  namespace_id = azurerm_servicebus_namespace.main.id
  
  listen = true
  send   = true
  manage = false
}

# Output Service Bus connection string
output "servicebus_connection_string" {
  value       = azurerm_servicebus_namespace_authorization_rule.qlp_services.primary_connection_string
  sensitive   = true
  description = "Primary connection string for Service Bus namespace"
}