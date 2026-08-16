variable "rg_details" {
  description = "Map of resource group configurations"
  type = map(object({
    name        = string
    location    = string
    environment = optional(string, "unknown")
    workload    = optional(string, "")
    cost_center = optional(string, "untagged")
    data_class  = optional(string, "internal")
    enable_lock = optional(bool, true)
    tags        = optional(map(string), {})
  }))
}