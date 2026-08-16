# =============================================================================
# virtual_network — Hardened
# Security controls: DDoS Protection Plan, mandatory tags, isolated per workload
# Each VNet is isolated by design — no peering without explicit variable
# =============================================================================

resource "azurerm_virtual_network" "vnets" {
  for_each            = var.vnet_details
  name                = each.value.name
  resource_group_name = each.value.resource
  location            = each.value.location
  address_space       = each.value.space

  # DDoS Protection — attach a shared plan when provided
  dynamic "ddos_protection_plan" {
    for_each = lookup(each.value, "ddos_protection_plan_id", null) != null ? [1] : []
    content {
      id     = each.value.ddos_protection_plan_id
      enable = true
    }
  }

  # DNS — use Azure-provided by default; override per VNet for custom DNS
  dns_servers = lookup(each.value, "dns_servers", [])

  tags = merge(
    {
      environment = lookup(each.value, "environment", "unknown")
      workload    = lookup(each.value, "workload", each.key)
      managed_by  = "terraform"
    },
    lookup(each.value, "tags", {})
  )
}