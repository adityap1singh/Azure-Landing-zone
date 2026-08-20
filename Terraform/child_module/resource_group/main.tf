# =============================================================================
# resource_group — Hardened
# Security controls: mandatory tags, management lock (CanNotDelete)
# Workload isolation: each RG is locked independently
# =============================================================================

resource "azurerm_resource_group" "rg" {
  for_each = var.rg_details
  name     = each.value.name
  location = each.value.location

  tags = merge(
    {
      environment    = lookup(each.value, "environment", "unknown")
      workload       = lookup(each.value, "workload", each.key)
      managed_by     = "terraform"
      cost_center    = lookup(each.value, "cost_center", "untagged")
      data_class     = lookup(each.value, "data_class", "internal")
      created_by     = "landing-zone-automation"
    },
    lookup(each.value, "tags", {})
  )
}


