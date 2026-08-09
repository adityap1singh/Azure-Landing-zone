resource "azurerm_kubernetes_cluster" "aks" {
  for_each            = var.aks_details
  name                = each.value.name
  location            = each.value.location
  resource_group_name = lookup(each.value, "resource_group_name", lookup(each.value, "resource", null))
  dns_prefix          = lookup(each.value, "dns_prefix", "${each.value.name}-dns")
  kubernetes_version  = lookup(each.value, "kubernetes_version", null)

  default_node_pool {
    name                 = lookup(each.value, "node_pool_name", "default")
    node_count           = lookup(each.value, "node_count", 1)
    vm_size              = lookup(each.value, "vm_size", "Standard_D2s_v3")
    vnet_subnet_id       = lookup(each.value, "vnet_subnet_id", null)
    auto_scaling_enabled = lookup(each.value, "auto_scaling_enabled", false)
    min_count            = lookup(each.value, "auto_scaling_enabled", false) ? lookup(each.value, "min_count", 1) : null
    max_count            = lookup(each.value, "auto_scaling_enabled", false) ? lookup(each.value, "max_count", 3) : null
  }


  identity {
    type = "SystemAssigned"
  }


  dynamic "network_profile" {
    for_each = lookup(each.value, "network_plugin", null) != null ? [1] : []
    content {
      network_plugin    = lookup(each.value, "network_plugin", "kubenet")
      load_balancer_sku = lookup(each.value, "load_balancer_sku", "standard")
    }
  }

  tags = lookup(each.value, "tags", null)
}

# Role Assignment: Allow AKS Kubelet identity to pull images from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  for_each                         = { for k, v in var.aks_details : k => v if lookup(v, "acr_id", null) != null }
  principal_id                     = azurerm_kubernetes_cluster.aks[each.key].kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = each.value.acr_id
  skip_service_principal_aad_check = true
}

