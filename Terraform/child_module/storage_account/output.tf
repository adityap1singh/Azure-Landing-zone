output "storage" {
    value = {for k , v in azurerm_storage_account.store1: v.name => v.id}
  
}