resource "aws_cloudwatch_event_rule" "notifications_event_rule" {
  for_each = var.schedules

  name                = "${var.rule_name_prefix}-${each.key}"
  description         = each.value.description
  schedule_expression = each.value.cron_expression
  state               = each.value.state

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "lambda_event_target" {
  for_each = var.schedules

  rule      = aws_cloudwatch_event_rule.notifications_event_rule[each.key].name
  target_id = "lambda-target-${each.key}"
  arn       = var.lambda_function_arn

  input = jsonencode({
    trigger_type = each.key
    timezone     = var.timezone
  })
}

resource "aws_lambda_permission" "lambda_permission" {
  for_each = var.schedules

  statement_id  = "AllowExecutionFromEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.notifications_event_rule[each.key].arn
}
