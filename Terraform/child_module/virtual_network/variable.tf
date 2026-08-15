variable "vnet_details" {
  description = "Map of virtual network configurations"
  type = map(object({
    name                    = string
    resource                = string
    location                = string
    space                   = list(string)
    dns_servers             = optional(list(string), [])
    ddos_protection_plan_id = optional(string, null)
    environment             = optional(string, "unknown")
    workload                = optional(string, "")
    tags                    = optional(map(string), {})
  }))
}