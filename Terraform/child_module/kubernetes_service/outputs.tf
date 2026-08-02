output "aks_id" {
  value = { for k, v in azurerm_kubernetes_cluster.aks : k => v.id }
}

output "aks_name" {
  value = { for k, v in azurerm_kubernetes_cluster.aks : k => v.name }
}

output "aks_kube_config" {
  value     = { for k, v in azurerm_kubernetes_cluster.aks : k => v.kube_config_raw }
  sensitive = true
}

output "aks_node_resource_group" {
  value = { for k, v in azurerm_kubernetes_cluster.aks : k => v.node_resource_group }
}
