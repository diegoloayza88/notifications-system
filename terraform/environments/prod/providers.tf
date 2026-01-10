provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "EventNotifications"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

