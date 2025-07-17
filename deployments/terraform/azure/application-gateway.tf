# Application Gateway for Production Ingress

# Public IP for Application Gateway
resource "azurerm_public_ip" "appgw" {
  name                = "${var.project_name}-appgw-pip-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  tags                = var.tags
}

# Subnet for Application Gateway
resource "azurerm_subnet" "appgw" {
  name                 = "appgw-subnet"
  resource_group_name  = data.azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]
}

# Application Gateway
resource "azurerm_application_gateway" "main" {
  name                = "${var.project_name}-appgw-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  zones               = ["1", "2", "3"]
  
  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 2
  }
  
  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = azurerm_subnet.appgw.id
  }
  
  frontend_port {
    name = "http"
    port = 80
  }
  
  frontend_port {
    name = "https"
    port = 443
  }
  
  frontend_ip_configuration {
    name                 = "frontend"
    public_ip_address_id = azurerm_public_ip.appgw.id
  }
  
  backend_address_pool {
    name = "aks-backend"
  }
  
  backend_http_settings {
    name                  = "http-settings"
    cookie_based_affinity = "Disabled"
    port                  = 8000
    protocol              = "Http"
    request_timeout       = 600
    probe_name           = "health-probe"
  }
  
  probe {
    name                = "health-probe"
    protocol            = "Http"
    path                = "/health"
    host                = "127.0.0.1"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3
  }
  
  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "frontend"
    frontend_port_name             = "http"
    protocol                       = "Http"
  }
  
  request_routing_rule {
    name                       = "http-rule"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "aks-backend"
    backend_http_settings_name = "http-settings"
    priority                   = 100
  }
  
  tags = var.tags
  
  lifecycle {
    ignore_changes = [
      backend_address_pool,
      backend_http_settings,
      request_routing_rule,
      probe,
      url_path_map,
      tags["ingress-for-aks-cluster-name"],
      tags["last-updated-by-k8s-ingress"],
      tags["managed-by-k8s-ingress"],
    ]
  }
}

# Install AGIC (Application Gateway Ingress Controller) on AKS
resource "helm_release" "agic" {
  name       = "ingress-azure"
  repository = "https://appgwingress.blob.core.windows.net/ingress-azure-helm-package/"
  chart      = "ingress-azure"
  namespace  = "kube-system"
  
  set {
    name  = "appgw.subscriptionId"
    value = data.azurerm_client_config.current.subscription_id
  }
  
  set {
    name  = "appgw.resourceGroup"
    value = data.azurerm_resource_group.main.name
  }
  
  set {
    name  = "appgw.name"
    value = azurerm_application_gateway.main.name
  }
  
  set {
    name  = "appgw.shared"
    value = "false"
  }
  
  set {
    name  = "armAuth.type"
    value = "workloadIdentity"
  }
  
  set {
    name  = "armAuth.identityClientID"
    value = azurerm_user_assigned_identity.agic.client_id
  }
  
  set {
    name  = "rbac.enabled"
    value = "true"
  }
  
  depends_on = [
    azurerm_application_gateway.main,
    azurerm_federated_identity_credential.agic,
    azurerm_role_assignment.agic_contributor
  ]
}

# User Assigned Identity for AGIC
resource "azurerm_user_assigned_identity" "agic" {
  name                = "${var.project_name}-agic-identity-${var.environment}"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = var.tags
}

# Federated Identity Credential for AGIC
resource "azurerm_federated_identity_credential" "agic" {
  name                = "agic-federated-credential"
  resource_group_name = data.azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.agic.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  subject             = "system:serviceaccount:kube-system:ingress-azure"
}

# Grant AGIC identity permissions on Application Gateway
resource "azurerm_role_assignment" "agic_contributor" {
  scope                = azurerm_application_gateway.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.agic.principal_id
}

# Grant AGIC identity permissions on Resource Group
resource "azurerm_role_assignment" "agic_reader" {
  scope                = data.azurerm_resource_group.main.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.agic.principal_id
}

# Output the Application Gateway IP
output "application_gateway_ip" {
  value = azurerm_public_ip.appgw.ip_address
}

output "application_gateway_fqdn" {
  value = azurerm_public_ip.appgw.fqdn
}