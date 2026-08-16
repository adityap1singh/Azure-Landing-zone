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

# Management Lock — prevent accidental deletion of resource groups
# Override with lock_level = "none" in tfvars to disable for a specific RG
resource "azurerm_management_lock" "rg_lock" {
  for_each = {
    for k, v in var.rg_details : k => v
    if lookup(v, "enable_lock", true)
  }
  name       = "lock-${each.value.name}"
  scope      = azurerm_resource_group.rg[each.key].id
  lock_level = "CanNotDelete"
  notes      = "Managed by Terraform — Azure Landing Zone. Remove lock before destroying."
}
