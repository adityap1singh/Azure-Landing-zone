resource "azurerm_kubernetes_cluster" "aks" {
  for_each            = var.aks_details
  name                = each.value.name
  location            = each.value.location
  resource_group_name = each.value.resource_group_name
  dns_prefix          = each.value.dns_prefix

  default_node_pool {
    name       = lookup(each.value, "node_pool_name", "default")
    node_count = lookup(each.value, "node_count", 1)
    vm_size    = lookup(each.value, "vm_size", "Standard_D2s_v3")
  }

  identity {
    type = "SystemAssigned"
  }
}

# Role Assignment: Allow AKS to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  for_each             = { for k, v in var.aks_details : k => v if lookup(v, "acr_id", null) != null }
  principal_id         = azurerm_kubernetes_cluster.aks[each.key].kubelet_identity[0].object_id
  role_definition_name = "AcrPull"
  scope                = each.value.acr_id
}
