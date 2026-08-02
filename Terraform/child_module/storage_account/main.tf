resource "azurerm_storage_account" "store1" {
    for_each = var.storage_details
    name = each.value.name
  location = each.value.location
  resource_group_name = each.value.resource
  account_tier = each.value.tier
  account_replication_type = each.value.type
}




