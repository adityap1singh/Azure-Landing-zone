resource "azurerm_container_registry" "acr" {
  for_each            = var.acr_details
  name                = each.value.name
  resource_group_name = each.value.resource_group_name
  location            = each.value.location
  sku                 = "Basic"
  admin_enabled       = false
}
