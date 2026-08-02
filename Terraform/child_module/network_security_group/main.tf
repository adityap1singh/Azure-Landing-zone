resource "azurerm_network_security_group" "nsg12" {
    for_each = var.nsg_details
    name = each.value.name
  resource_group_name = each.value.resource
  location = each.value.location
  
}