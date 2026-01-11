variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "event-notifications"
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
}

variable "timezone" {
  description = "Timezone for processing"
  type        = string
  default     = "America/Lima"
}

variable "notification_emails" {
  description = "List of email addresses for notifications"
  type        = list(string)
}

variable "google_credentials_json" {
  description = "Google service account credentials JSON"
  type        = string
  sensitive   = true
}

variable "discord_webhook_url" {
  description = "Discord webhook URL"
  type        = string
  sensitive   = true
}

variable "concerts_sheet_id" {
  description = "Google Sheets ID for concerts"
  type        = string
}

variable "interviews_sheet_id" {
  description = "Google Sheets ID for interviews"
  type        = string
}

variable "study_sheet_id" {
  description = "Google Sheets ID for study schedule"
  type        = string
}

variable "google_calendar_id" {
  description = "Google Calendar ID for creating events"
  type        = string
  default     = ""
}

