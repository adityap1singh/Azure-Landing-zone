resource "azurerm_subnet" "subnet-dev" {
    for_each = var.sub_details
    name = each.value.name
  resource_group_name = each.value.resource
  virtual_network_name = each.value.virtual
  address_prefixes = each.value.address
}


