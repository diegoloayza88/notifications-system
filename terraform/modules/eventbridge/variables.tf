variable "rule_name_prefix" {
  description = "Prefix for EventBridge rule names"
  type        = string
}

variable "schedules" {
  description = "Map of schedule configurations"
  type = map(object({
    cron_expression = string
    description     = string
    state           = string
  }))
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to trigger"
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "timezone" {
  description = "Timezone for event processing"
  type        = string
  default     = "America/Lima"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
