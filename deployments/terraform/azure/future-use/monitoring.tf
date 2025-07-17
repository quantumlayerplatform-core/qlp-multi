# Monitoring and Observability Configuration

# Install Prometheus using Helm
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "55.5.0"
  namespace  = "monitoring"
  
  create_namespace = true
  
  values = [
    yamlencode({
      prometheus = {
        prometheusSpec = {
          retention = "30d"
          storageSpec = {
            volumeClaimTemplate = {
              spec = {
                storageClassName = "managed-premium"
                accessModes      = ["ReadWriteOnce"]
                resources = {
                  requests = {
                    storage = "50Gi"
                  }
                }
              }
            }
          }
          serviceMonitorSelectorNilUsesHelmValues = false
          podMonitorSelectorNilUsesHelmValues     = false
          ruleSelectorNilUsesHelmValues           = false
        }
      }
      grafana = {
        adminPassword = random_password.grafana_admin.result
        persistence = {
          enabled          = true
          storageClassName = "managed-premium"
          size            = "10Gi"
        }
        ingress = {
          enabled = true
          annotations = {
            "kubernetes.io/ingress.class"                = "nginx"
            "cert-manager.io/cluster-issuer"             = "letsencrypt-prod"
            "nginx.ingress.kubernetes.io/ssl-redirect"   = "true"
          }
          hosts = ["grafana.${var.project_name}.${var.domain}"]
          tls = [{
            secretName = "grafana-tls"
            hosts      = ["grafana.${var.project_name}.${var.domain}"]
          }]
        }
      }
      alertmanager = {
        alertmanagerSpec = {
          storage = {
            volumeClaimTemplate = {
              spec = {
                storageClassName = "managed-premium"
                accessModes      = ["ReadWriteOnce"]
                resources = {
                  requests = {
                    storage = "10Gi"
                  }
                }
              }
            }
          }
        }
      }
    })
  ]
  
  depends_on = [azurerm_kubernetes_cluster.aks]
}

# Random password for Grafana admin
resource "random_password" "grafana_admin" {
  length  = 16
  special = true
}

# Store Grafana password in Key Vault
resource "azurerm_key_vault_secret" "grafana_password" {
  name         = "grafana-admin-password"
  value        = random_password.grafana_admin.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_role_assignment.current_user_kv]
}

# Install Jaeger for distributed tracing
resource "helm_release" "jaeger" {
  name       = "jaeger"
  repository = "https://jaegertracing.github.io/helm-charts"
  chart      = "jaeger"
  version    = "0.71.14"
  namespace  = "monitoring"
  
  values = [
    yamlencode({
      provisionDataStore = {
        cassandra = false
        elasticsearch = true
      }
      storage = {
        type = "elasticsearch"
        elasticsearch = {
          create = true
          nodeCount = 3
          persistence = {
            enabled = true
            storageClass = "managed-premium"
            size = "20Gi"
          }
        }
      }
      query = {
        ingress = {
          enabled = true
          annotations = {
            "kubernetes.io/ingress.class"              = "nginx"
            "cert-manager.io/cluster-issuer"           = "letsencrypt-prod"
            "nginx.ingress.kubernetes.io/ssl-redirect" = "true"
          }
          hosts = [{
            host = "jaeger.${var.project_name}.${var.domain}"
            paths = ["/"]
          }]
          tls = [{
            secretName = "jaeger-tls"
            hosts      = ["jaeger.${var.project_name}.${var.domain}"]
          }]
        }
      }
    })
  ]
  
  depends_on = [helm_release.prometheus]
}

# Container Insights Dashboard
resource "azurerm_portal_dashboard" "aks_monitoring" {
  name                 = "${var.project_name}-aks-dashboard-${var.environment}"
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  dashboard_properties = templatefile("${path.module}/templates/aks-dashboard.json", {
    subscription_id     = data.azurerm_client_config.current.subscription_id
    resource_group_name = azurerm_resource_group.main.name
    aks_name           = azurerm_kubernetes_cluster.aks.name
    workspace_id       = azurerm_log_analytics_workspace.main.id
  })
  
  tags = var.tags
}

# Log Analytics Queries for monitoring
resource "azurerm_log_analytics_saved_search" "qlp_queries" {
  for_each = {
    "pod_restart_count" = {
      display_name = "QLP Pod Restart Count"
      query       = "KubePodInventory | where Namespace == 'qlp-production' | summarize RestartCount = sum(RestartCount) by Name, bin(TimeGenerated, 5m)"
    }
    "error_logs" = {
      display_name = "QLP Error Logs"
      query       = "ContainerLog | where LogEntry contains 'ERROR' and ContainerName startswith 'qlp-' | project TimeGenerated, ContainerName, LogEntry | order by TimeGenerated desc"
    }
    "api_latency" = {
      display_name = "QLP API Latency"
      query       = "AppRequests | where Name startswith '/api/' | summarize avg(DurationMs), percentile(DurationMs, 95), percentile(DurationMs, 99) by bin(TimeGenerated, 5m), Name"
    }
  }
  
  name                       = each.key
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  category                   = "QLP Monitoring"
  display_name              = each.value.display_name
  query                     = each.value.query
}

# Azure Monitor Action Group for alerts
resource "azurerm_monitor_action_group" "main" {
  name                = "${var.project_name}-alerts-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "qlpalerts"
  
  email_receiver {
    name          = "ops-team"
    email_address = var.ops_email
  }
  
  webhook_receiver {
    name        = "slack-webhook"
    service_uri = var.slack_webhook_url
  }
  
  tags = var.tags
}

# Metric Alerts
resource "azurerm_monitor_metric_alert" "high_cpu" {
  name                = "${var.project_name}-high-cpu-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_kubernetes_cluster.aks.id]
  description         = "Alert when CPU usage is over 80%"
  
  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_cpu_usage_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.tags
}

resource "azurerm_monitor_metric_alert" "pod_failures" {
  name                = "${var.project_name}-pod-failures-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_kubernetes_cluster.aks.id]
  description         = "Alert when pods are failing"
  
  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "kube_pod_status_phase"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 1
    
    dimension {
      name     = "phase"
      operator = "Include"
      values   = ["Failed"]
    }
    
    dimension {
      name     = "namespace"
      operator = "Include"
      values   = ["qlp-production"]
    }
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.tags
}