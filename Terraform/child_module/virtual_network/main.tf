resource "azurerm_virtual_network" "vnets" {
    for_each = var.vnet_details
    name = each.value.name
  resource_group_name = each.value.resource
  location = each.value.location
  address_space = each.value.space
  
}