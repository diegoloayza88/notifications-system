output "secret_arns" {
  description = "ARNs of the secrets"
  value       = { for k, v in aws_secretsmanager_secret.notifications_secret : k => v.arn }
}

output "secret_names" {
  description = "Names of the secrets"
  value       = { for k, v in aws_secretsmanager_secret.notifications_secret : k => v.name }
}
