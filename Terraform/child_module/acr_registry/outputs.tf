output "acr_login_server" {
  value = { for k, v in azurerm_container_registry.acr : k => v.login_server }
}

output "acr_id" {
  value = { for k, v in azurerm_container_registry.acr : k => v.id }
}

output "acr_name" {
  value = { for k, v in azurerm_container_registry.acr :k => v.name }
}


