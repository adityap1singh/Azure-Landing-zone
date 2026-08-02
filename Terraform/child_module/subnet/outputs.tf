output "subnet_ids" {
  value = { for k, v in azurerm_subnet.subnet-dev : k => v.id }
}
