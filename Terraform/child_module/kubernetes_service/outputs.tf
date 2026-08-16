output "aks_id" {
  description = "Map of AKS cluster IDs"
  value       = { for k, v in azurerm_kubernetes_cluster.aks : k => v.id }
}

output "aks_name" {
  description = "Map of AKS cluster names"
  value       = { for k, v in azurerm_kubernetes_cluster.aks : k => v.name }
}

output "aks_kube_config" {
  description = "Raw Kubeconfig output for each AKS cluster"
  value       = { for k, v in azurerm_kubernetes_cluster.aks : k => v.kube_config_raw }
  sensitive   = true
}

output "aks_node_resource_group" {
  description = "Map of node resource groups for each cluster"
  value       = { for k, v in azurerm_kubernetes_cluster.aks : k => v.node_resource_group }
}

output "aks_kubelet_identity_object_id" {
  description = "Map of Kubelet Identity Object IDs for role assignments"
  value       = { for k, v in azurerm_kubernetes_cluster.aks : k => v.kubelet_identity[0].object_id }
}

