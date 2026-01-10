resource "aws_lambda_function" "notifications" {
  filename         = var.lambda_package_path
  function_name    = var.function_name
  role             = aws_iam_role.lambda.arn
  handler          = var.handler
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size
  source_code_hash = filebase64sha256(var.lambda_package_path)

  environment {
    variables = merge(
      var.environment_variables,
      {
        DYNAMODB_TABLE     = var.dynamodb_table_name
        SNS_TOPIC_ARN      = var.sns_topic_arn
        DISCORD_WEBHOOK    = var.discord_webhook_secret_arn
        GOOGLE_CREDENTIALS = var.google_credentials_secret_arn
      }
    )
  }

  layers = var.lambda_layers

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}