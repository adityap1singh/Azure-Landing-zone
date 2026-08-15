output "rg_ids" {
  description = "Map of resource group names to their Azure resource IDs"
  value       = { for k, v in azurerm_resource_group.rg : k => v.id }
}

output "rg_names" {
  description = "Map of resource group keys to their names"
  value       = { for k, v in azurerm_resource_group.rg : k => v.name }
}

output "rg_locations" {
  description = "Map of resource group keys to their locations"
  value       = { for k, v in azurerm_resource_group.rg : k => v.location }
}
