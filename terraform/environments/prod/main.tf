locals {
  common_tags = {
    Project     = "EventNotifications"
    Environment = var.environment
    Owner       = var.owner
  }
}

module "secrets" {
  source = "../../modules/secrets"

  secret_prefix = "${var.project_name}-${var.environment}"

  secrets = {
    google-credentials = {
      description = "Google Sheets API credentials"
      value       = var.google_credentials_json
    }
    discord-webhook = {
      description = "Discord webhook URL"
      value       = var.discord_webhook_url
    }
  }

  tags = local.common_tags
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  table_name   = "${var.project_name}-${var.environment}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"
  range_key    = "event_type"

  attributes = [
    {
      name = "event_id"
      type = "S"
    },
    {
      name = "event_type"
      type = "S"
    },
    {
      name = "event_date"
      type = "S"
    },
    {
      name = "sheet_hash"
      type = "S"
    }
  ]

  global_secondary_indexes = [
    {
      name            = "EventDateIndex"
      hash_key        = "event_type"
      range_key       = "event_date"
      projection_type = "ALL"
      read_capacity   = 0
      write_capacity  = 0
    },
    {
      name            = "SheetHashIndex"
      hash_key        = "sheet_hash"
      range_key       = "event_type"
      projection_type = "ALL"
      read_capacity   = 0
      write_capacity  = 0
    }
  ]

  point_in_time_recovery = true
  server_side_encryption = true

  tags = local.common_tags
}

module "sns" {
  source = "../../modules/sns"

  topic_name      = "${var.project_name}-${var.environment}-notifications"
  display_name    = "Event Notifications"
  email_addresses = var.notification_emails

  tags = local.common_tags
}

module "lambda" {
  source = "../../modules/lambda"

  function_name       = "${var.project_name}-${var.environment}-processor"
  lambda_package_path = "${path.module}/lambda.zip"
  handler             = "handler.main"
  runtime             = "python3.13"
  timeout             = 300
  memory_size         = 512

  dynamodb_table_name = module.dynamodb.table_name
  dynamodb_table_arn  = module.dynamodb.table_arn
  sns_topic_arn       = module.sns.topic_arn

  google_credentials_secret_arn = module.secrets.secret_arns["google-credentials"]
  discord_webhook_secret_arn    = module.secrets.secret_arns["discord-webhook"]

  environment_variables = {
    ENVIRONMENT         = var.environment
    TIMEZONE            = var.timezone
    CONCERTS_SHEET_ID   = var.concerts_sheet_id
    INTERVIEWS_SHEET_ID = var.interviews_sheet_id
    STUDY_SHEET_ID      = var.study_sheet_id
  }

  log_retention_days = 7

  tags = local.common_tags
}

module "eventbridge" {
  source = "../../modules/eventbridge"

  rule_name_prefix     = "${var.project_name}-${var.environment}"
  lambda_function_arn  = module.lambda.function_arn
  lambda_function_name = module.lambda.function_name
  timezone             = var.timezone

  schedules = {
    morning-check = {
      cron_expression = "cron(0 11 * * ? *)" # 6am GMT-5
      description     = "Morning notification check"
      state           = "ENABLED"
    }
    evening-check = {
      cron_expression = "cron(0 23 * * ? *)" # 6pm GMT-5
      description     = "Evening study reminder check"
      state           = "ENABLED"
    }
    afternoon-check = {
      cron_expression = "cron(0 18 * * ? *)" # 1pm GMT-5
      description     = "Afternoon notification check"
      state           = "ENABLED"
    }
    hourly-urgent = {
      cron_expression = "cron(0 * * * ? *)" # Every hour for urgent notifications
      description     = "Hourly check for imminent events"
      state           = "ENABLED"
    }
  }

  tags = local.common_tags
}
