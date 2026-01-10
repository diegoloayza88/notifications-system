resource "aws_secretsmanager_secret" "notifications_secret" {
  for_each = var.secrets

  name        = "${var.secret_prefix}/${each.key}"
  description = each.value.description

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "notifications_secret_version" {
  for_each = var.secrets

  secret_id     = aws_secretsmanager_secret.notifications_secret[each.key].id
  secret_string = each.value.value
}
