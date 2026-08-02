resource "azurerm_network_interface" "main" {
  for_each            = var.network_details
  name                = each.value.name
  location            = each.value.location
  resource_group_name = each.value.resource

  ip_configuration {
    name                          = "ipconfiguration14679"
    subnet_id                     = var.sub_details[each.value.subnet_id]
    private_ip_address_allocation = "Dynamic"
  }
}