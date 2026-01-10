output "rule_arns" {
  description = "ARNs of the EventBridge rules"
  value       = { for k, v in aws_cloudwatch_event_rule.notifications_event_rule : k => v.arn }
}

output "rule_names" {
  description = "Names of the EventBridge rules"
  value       = { for k, v in aws_cloudwatch_event_rule.notifications_event_rule : k => v.name }
}
