# =============================================================================
# subnet — Hardened
# Security controls:
#   • Service endpoints for PaaS services (Key Vault, Storage, SQL, ACR)
#   • Private endpoint network policies disabled (required for PE)
#   • Private link service network policies disabled
#   • NSG association managed via nsg_associations variable
#   • Workload isolation: each subnet scoped to exactly one workload
# =============================================================================

resource "azurerm_subnet" "subnets" {
  for_each             = var.sub_details
  name                 = each.value.name
  resource_group_name  = each.value.resource
  virtual_network_name = each.value.virtual
  address_prefixes     = each.value.address

  # Service endpoints — allow subnets to reach PaaS over Azure backbone (no public internet)
  service_endpoints = lookup(each.value, "service_endpoints", [
    "Microsoft.KeyVault",
    "Microsoft.Storage",
    "Microsoft.Sql",
    "Microsoft.ContainerRegistry",
    "Microsoft.ServiceBus",
  ])

  # Required for Private Endpoints to work on this subnet
  private_endpoint_network_policies             = "Disabled"
  private_link_service_network_policies_enabled = false

  # Delegation (e.g. for AKS, App Service) — optional
  dynamic "delegation" {
    for_each = lookup(each.value, "delegation_name", null) != null ? [1] : []
    content {
      name = each.value.delegation_name
      service_delegation {
        name    = each.value.delegation_service
        actions = lookup(each.value, "delegation_actions", [])
      }
    }
  }
}

# NSG Association — each subnet gets its own NSG for workload isolation
resource "azurerm_subnet_network_security_group_association" "nsg_assoc" {
  for_each = {
    for k, v in var.sub_details : k => v
    if lookup(v, "nsg_id", null) != null
  }
  subnet_id                 = azurerm_subnet.subnets[each.key].id
  network_security_group_id = each.value.nsg_id
}
