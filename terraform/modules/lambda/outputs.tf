output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.notifications.arn
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.notifications.function_name
}

output "role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_log_group.name
}
