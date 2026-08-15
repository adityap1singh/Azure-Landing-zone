variable "sub_details" {
  description = "Map of subnet configurations with security hardening options"
  type = map(object({
    name               = string
    resource           = string
    virtual            = string
    address            = list(string)
    service_endpoints  = optional(list(string), [])
    nsg_id             = optional(string, null)
    delegation_name    = optional(string, null)
    delegation_service = optional(string, null)
    delegation_actions = optional(list(string), [])
  }))
}
