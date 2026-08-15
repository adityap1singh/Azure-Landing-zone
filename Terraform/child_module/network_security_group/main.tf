# =============================================================================
# network_security_group — Hardened
# Security controls:
#   • Deny-all inbound/outbound as base rules (highest priority = lowest number wins)
#   • Explicit allow rules injected via variables
#   • Allow-list model: nothing passes unless explicitly permitted
#   • Each NSG is scoped to one workload — no shared NSGs across workloads
# =============================================================================

resource "azurerm_network_security_group" "nsg" {
  for_each            = var.nsg_details
  name                = each.value.name
  resource_group_name = each.value.resource
  location            = each.value.location

  tags = merge(
    {
      environment = lookup(each.value, "environment", "unknown")
      workload    = lookup(each.value, "workload", each.key)
      managed_by  = "terraform"
    },
    lookup(each.value, "tags", {})
  )
}

# ── Deny-All Inbound (base rule, priority 4096 = last resort) ────────────────
resource "azurerm_network_security_rule" "deny_all_inbound" {
  for_each                    = var.nsg_details
  name                        = "DenyAllInbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = each.value.resource
  network_security_group_name = azurerm_network_security_group.nsg[each.key].name
}

# ── Deny-All Outbound (base rule) ────────────────────────────────────────────
resource "azurerm_network_security_rule" "deny_all_outbound" {
  for_each                    = var.nsg_details
  name                        = "DenyAllOutbound"
  priority                    = 4096
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = each.value.resource
  network_security_group_name = azurerm_network_security_group.nsg[each.key].name
}

# ── Allow Azure Load Balancer probes (required for AKS, VMs, etc.) ───────────
resource "azurerm_network_security_rule" "allow_azure_lb" {
  for_each                    = var.nsg_details
  name                        = "AllowAzureLoadBalancerInbound"
  priority                    = 4000
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "AzureLoadBalancer"
  destination_address_prefix  = "*"
  resource_group_name         = each.value.resource
  network_security_group_name = azurerm_network_security_group.nsg[each.key].name
}

# ── Allow Azure Monitor / Bastion service tags ────────────────────────────────
resource "azurerm_network_security_rule" "allow_bastion_control" {
  for_each = {
    for k, v in var.nsg_details : k => v
    if lookup(v, "allow_bastion", false)
  }
  name                        = "AllowBastionHostCommunication"
  priority                    = 3990
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["22", "3389"]
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = each.value.resource
  network_security_group_name = azurerm_network_security_group.nsg[each.key].name
}

# ── User-defined explicit allow rules ────────────────────────────────────────
# Passed in via nsg_rules variable — allows workload-specific rules
resource "azurerm_network_security_rule" "custom_rules" {
  for_each = var.nsg_rules

  name                        = each.value.name
  priority                    = each.value.priority
  direction                   = each.value.direction
  access                      = each.value.access
  protocol                    = each.value.protocol
  source_port_range           = lookup(each.value, "source_port_range", "*")
  destination_port_range      = lookup(each.value, "destination_port_range", null)
  destination_port_ranges     = lookup(each.value, "destination_port_ranges", null)
  source_address_prefix       = lookup(each.value, "source_address_prefix", "*")
  destination_address_prefix  = lookup(each.value, "destination_address_prefix", "*")
  resource_group_name         = each.value.resource_group_name
  network_security_group_name = azurerm_network_security_group.nsg[each.value.nsg_key].name

  lifecycle {
    create_before_destroy = true
  }
}