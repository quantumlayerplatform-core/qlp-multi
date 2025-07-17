# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.project_name}-postgres-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = var.postgres_admin_username
  administrator_password = var.postgres_admin_password
  
  sku_name   = var.postgres_sku
  storage_mb = 131072  # 128 GB
  
  backup_retention_days        = 35
  geo_redundant_backup_enabled = true
  auto_grow_enabled           = true
  
  delegated_subnet_id = azurerm_subnet.services.id
  private_dns_zone_id = azurerm_private_dns_zone.postgres.id
  
  high_availability {
    mode                      = "ZoneRedundant"
    standby_availability_zone = "2"
  }
  
  maintenance_window {
    day_of_week  = 0  # Sunday
    start_hour   = 2
    start_minute = 0
  }
  
  tags = var.tags
  
  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "qlp" {
  name      = "qlp_db"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

# PostgreSQL Firewall Rules
resource "azurerm_postgresql_flexible_server_firewall_rule" "aks" {
  name             = "allow-aks-subnet"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  resource_group_name   = azurerm_resource_group.main.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
  tags                  = var.tags
}

# Redis Cache
resource "azurerm_redis_cache" "main" {
  name                = "${var.project_name}-redis-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 2
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  
  redis_configuration {
    maxmemory_policy = "allkeys-lru"
    enable_authentication = true
  }
  
  # Enable zone redundancy in UK South
  zones = ["1", "2"]
  
  tags = var.tags
}

# Cosmos DB Account (for document storage)
resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.project_name}-cosmos-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  
  enable_automatic_failover = true
  enable_multiple_write_locations = false
  
  consistency_policy {
    consistency_level       = var.cosmos_consistency_level
    max_interval_in_seconds = 10
    max_staleness_prefix    = 200
  }
  
  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
    zone_redundant    = true
  }
  
  geo_location {
    location          = "ukwest"
    failover_priority = 1
    zone_redundant    = true
  }
  
  capabilities {
    name = "EnableServerless"
  }
  
  backup {
    type                = "Continuous"
    tier                = "Continuous30Days"
  }
  
  tags = var.tags
}

# Cosmos DB SQL Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "qlp-database"
  resource_group_name = azurerm_cosmosdb_account.main.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Cosmos DB Container for capsules
resource "azurerm_cosmosdb_sql_container" "capsules" {
  name                  = "capsules"
  resource_group_name   = azurerm_cosmosdb_account.main.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_path    = "/capsule_id"
  partition_key_version = 1
  
  indexing_policy {
    indexing_mode = "consistent"
    
    included_path {
      path = "/*"
    }
    
    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# Storage Account for blob storage
resource "azurerm_storage_account" "main" {
  name                     = "${var.project_name}storage${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  
  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 30
    }
    
    container_delete_retention_policy {
      days = 30
    }
  }
  
  network_rules {
    default_action             = "Allow"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [azurerm_subnet.aks.id]
  }
  
  tags = var.tags
}

# Storage Container for capsule artifacts
resource "azurerm_storage_container" "capsules" {
  name                  = "capsule-artifacts"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Storage Container for temporary files
resource "azurerm_storage_container" "temp" {
  name                  = "temp-files"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}