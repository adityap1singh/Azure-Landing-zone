output "vnet_ids" {
  description = "Map of VNet keys to their Azure resource IDs"
  value       = { for k, v in azurerm_virtual_network.vnets : k => v.id }
}

output "vnet_names" {
  description = "Map of VNet keys to their names"
  value       = { for k, v in azurerm_virtual_network.vnets : k => v.name }
}
