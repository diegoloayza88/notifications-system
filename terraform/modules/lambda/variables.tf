variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "lambda_package_path" {
  description = "Path to Lambda deployment package"
  type        = string
}

variable "handler" {
  description = "Lambda handler"
  type        = string
  default     = "handler.main"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.11"
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "environment_variables" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for state tracking"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  type        = string
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for email notifications"
  type        = string
}

variable "google_credentials_secret_arn" {
  description = "Secrets Manager ARN for Google credentials"
  type        = string
}

variable "discord_webhook_secret_arn" {
  description = "Secrets Manager ARN for Discord webhook"
  type        = string
}

variable "lambda_layers" {
  description = "Lambda layers ARNs"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch logs retention in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
