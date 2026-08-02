output "network_name" {
  value = { for k, v in azurerm_network_interface.main : k => v.name}
}

output "network_id" {
  value = { for k, v in azurerm_network_interface.main : k => v.id}
}