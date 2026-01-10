resource "aws_sns_topic" "notifications_topic" {
  name              = var.topic_name
  display_name      = var.display_name
  kms_master_key_id = var.kms_master_key_id

  tags = var.tags
}

resource "aws_sns_topic_subscription" "notifications_topic_subscription" {
  for_each = toset(var.email_addresses)

  topic_arn = aws_sns_topic.notifications_topic.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_sns_topic_policy" "this" {
  arn = aws_sns_topic.notifications_topic.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowLambdaPublish"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action   = "SNS:Publish"
      Resource = aws_sns_topic.notifications_topic.arn
    }]
  })
}