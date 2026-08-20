resource "azurerm_virtual_machine" "main" {
  for_each              = var.virtual_machine
  name                  = each.value.name
  location              = each.value.location
  resource_group_name   = each.value.resource
  network_interface_ids = [var.network_interface_ids[each.value.network_id]]
  vm_size               = each.value.vm_size

  storage_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  storage_os_disk {
    name              = "osdisk-m"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  os_profile {
    computer_name  = "hostname-aditya"
    admin_username = "testadmin"
    admin_password = "Password1234!"
  }

  os_profile_linux_config {
    disable_password_authentication = false
  }
}
