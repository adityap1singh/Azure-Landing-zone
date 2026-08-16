output "acr_login_server" {
  description = "Map of ACR login servers"
  value       = { for k, v in azurerm_container_registry.acr : k => v.login_server }
}

output "acr_id" {
  description = "Map of ACR IDs"
  value       = { for k, v in azurerm_container_registry.acr : k => v.id }
}

output "acr_name" {
  description = "Map of ACR names"
  value       = { for k, v in azurerm_container_registry.acr : k => v.name }
}

output "acr_admin_username" {
  description = "Map of ACR admin usernames"
  value       = { for k, v in azurerm_container_registry.acr : k => v.admin_username }
  sensitive   = true
}



