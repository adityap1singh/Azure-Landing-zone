resource "azurerm_container_registry" "acr" {
  for_each            = var.acr_details
  name                = each.value.name
  resource_group_name = lookup(each.value, "resource_group_name", lookup(each.value, "resource", null))
  location            = each.value.location
  sku                 = lookup(each.value, "sku", "Basic")
  admin_enabled       = lookup(each.value, "admin_enabled", false)
  tags                = lookup(each.value, "tags", null)
}


