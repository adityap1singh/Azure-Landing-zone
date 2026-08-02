resource "azurerm_storage_container" "count12" {
  for_each = var.container_details
  name = each.value.name
  storage_account_id = var.storage_account_ids[each.value.storage_account_id]
  container_access_type = each.value.type
}