variable "secret_prefix" {
  description = "Prefix for secret names"
  type        = string
}

variable "secrets" {
  description = "Map of secrets to create"
  type = map(object({
    description = string
    value       = string
  }))
  sensitive = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
