resource "azurerm_public_ip" "pip1" {
  for_each            = var.pip_details
  name                = each.value.name
  location            = each.value.location
  resource_group_name = each.value.resource
  allocation_method   = each.value.allocation
}

resource "azurerm_bastion_host" "bastion123" {
  for_each            = var.pip_details
  name                = "bastion-${each.key}"
  resource_group_name = each.value.resource
  location            = each.value.location

  ip_configuration {
    name                 = "ipconfiguration"
    subnet_id            = var.subnet_ids["subn3"]
    public_ip_address_id = azurerm_public_ip.pip1[each.key].id
  }
}
