variable "nsg_details" {}

variable "nsg_rules" {
  description = "Optional custom NSG rules keyed by rule name or identifier."
  type        = map(any)
  default     = {}
}