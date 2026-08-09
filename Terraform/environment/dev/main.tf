module "resource" {
  source     = "../../child_module/resource_group"
  rg_details = var.rg_details
}

module "storage-account" {
  depends_on      = [module.resource]
  source          = "../../child_module/storage_account"
  storage_details = var.storage_details
}

module "storage-container" {
  depends_on          = [module.storage-account]
  source              = "../../child_module/storage_container"
  container_details   = var.container_details
  storage_account_ids = module.storage-account.storage
}

module "virtaul-network" {
  depends_on   = [module.resource]
  source       = "../../child_module/virtual_network"
  vnet_details = var.vnet_details
}

module "subnets" {
  depends_on  = [module.resource, module.virtaul-network]
  source      = "../../child_module/subnet"
  sub_details = var.sub_details
}


module "nsg-dev" {
  depends_on  = [module.resource]
  source      = "../../child_module/network_security_group"
  nsg_details = var.nsg_details
}

module "bastion-dev" {
  depends_on  = [module.resource, module.subnets]
  source      = "../../child_module/Bastion_host"
  pip_details = var.pip_details
  subnet_ids  = module.subnets.subnet_ids
}

module "virtual_machine" {
  depends_on            = [module.resource, module.subnets, module.network]
  source                = "../../child_module/virtual_machine"
  virtual_machine       = var.virtual_machine
  subnet_ids            = module.subnets.subnet_ids
  network_interface_ids = module.network.network_id
}


module "acr" {
  depends_on  = [module.resource]
  source      = "../../child_module/acr_registry"
  acr_details = var.acr_details
}

module "aks" {
  depends_on  = [module.resource, module.subnets, module.acr]
  source      = "../../child_module/kubernetes_service"
  aks_details = var.aks_details
}

module "network" {
  depends_on      = [module.resource, module.subnets]
  source          = "../../child_module/Network_interface"
  network_details = var.network_details
  sub_details     = module.subnets.subnet_ids
}