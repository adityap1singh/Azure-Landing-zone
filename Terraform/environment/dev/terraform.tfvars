rg_details = {
  rg1 = {
    name     = "rg_rg_rg1-aditya"
    location = "eastus"
  }

  rg2 = {
    name     = "rg_rg_rg2"
    location = "westus"
  }


}


storage_details = {
  store1 = {
    name     = "storeaccount3458234"
    location = "eastus"
    resource = "rg_rg_rg1-aditya"
    tier     = "Standard"
    type     = "ZRS"

  }
}

container_details = {
  count1 = {
    name               = "blob-container1"
    storage_account_id = "storeaccount3458234"
    type               = "private"
  }
}

vnet_details = {
  vnet1 = {
    name     = "vnet-dev"
    resource = "rg_rg_rg1-aditya"
    location = "eastus"
    space    = ["10.0.0.0/16"]
  }

  vnet2 = {
    name     = "dev-app"
    resource = "rg_rg_rg2"
    location = "westus"
    space    = ["10.0.0.0/16"]
  }
}


sub_details = {
  subn1 = {
    name     = "subnet-dev1"
    resource = "rg_rg_rg1-aditya"
    virtual  = "vnet-dev"
    address  = ["10.0.1.0/24"]
  }

  subn2 = {
    name     = "subnet-dev2"
    resource = "rg_rg_rg1-aditya"
    virtual  = "vnet-dev"
    address  = ["10.0.3.0/24"]
  }

  subn3 = {
    name     = "AzureBastionSubnet"
    resource = "rg_rg_rg1-aditya"
    virtual  = "vnet-dev"
    address  = ["10.0.7.0/24"]
  }

}

nsg_details = {
  nsg = {
    name     = "nsg-dev"
    resource = "rg_rg_rg1-aditya"
    location = "eastus"
  }
}

pip_details = {
  pipm = {
    name       = "pip12"
    location   = "eastus"
    resource   = "rg_rg_rg1-aditya"
    allocation = "Static"
  }

}

network_details = {
  nic1 = {
    name      = "nic1"
    location  = "eastus"
    resource  = "rg_rg_rg1-aditya"
    subnet_id = "subn1"
  }
}


virtual_machine = {
  vm = {
    name       = "VM-Linux-frontend"
    resource   = "rg_rg_rg1-aditya"
    vm_size    = "Standard_D2s_v7"
    location   = "eastus"
    subnet_id  = "subnet-dev1"
    network_id = "nic1"
  }

  vm1 = {
    name       = "VM-linux-backend"
    resource   = "rg_rg_rg1-aditya"
    vm_size    = "Standard_D2s_v7"
    location   = "eastus"
    subnet_id  = "subnet-dev1"
    network_id = "nic1"
  }
}

acr_details = {
  acr1 = {
    name                = "acraditya3"
    resource_group_name = "rg_rg_rg1-aditya"
    location            = "eastus"
    sku                 = "Basic"
    admin_enabled       = false
  }
}

aks_details = {
  aks1 = {
    name                = "aks-dev-cluster"
    resource_group_name = "rg_rg_rg1-aditya"
    location            = "eastus"
    dns_prefix          = "aksdevcluster"
    node_pool_name      = "default"
    node_count          = 2
    vm_size             = "Standard_D2s_v7"
  }
}
