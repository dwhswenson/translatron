# DynamoDB table
resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "conversation_id"
  range_key    = "timestamp"

  attribute {
    name = "timestamp"
    type = "S"
  }
  attribute {
    name = "message_id"
    type = "S"
  }
  attribute {
    name = "sender"
    type = "S"
  }
  attribute {
    name = "conversation_id"
    type = "S"
  }

  global_secondary_index {
    name            = "TimestampIndex"
    hash_key        = "timestamp"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "MessageIdIndex"
    hash_key        = "message_id"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "SenderIndex"
    hash_key        = "sender"
    projection_type = "ALL"
  }

  point_in_time_recovery { enabled = true }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Inline policy granting Lambda the right DynamoDB actions
resource "aws_iam_role_policy" "lambda_dynamo" {
  name = "${var.project_name}-${var.table_name}-dynamo-policy"
  role = var.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ]
      Resource = aws_dynamodb_table.this.arn
    }]
  })
}

# — Optional: Backups — 
# only if a vault name is passed
resource "aws_backup_vault" "this" {
  count = var.backup_vault_name != null ? 1 : 0
  name  = var.backup_vault_name
}

resource "aws_backup_plan" "this" {
  count = var.backup_vault_name != null ? 1 : 0
  name  = "${var.project_name}-${var.table_name}-backup-plan"

  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.this[0].name
    schedule          = var.backup_plan_schedule
    lifecycle { delete_after = var.backup_retention_days }
  }
}

resource "aws_iam_role" "backup" {
  count = var.backup_vault_name != null ? 1 : 0
  name  = "${var.project_name}-${var.table_name}-backup-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "backup.amazonaws.com" }
    }]
  })
}

resource "aws_backup_selection" "this" {
  count        = var.backup_vault_name != null ? 1 : 0
  iam_role_arn = aws_iam_role.backup[0].arn
  name         = "${var.project_name}-${var.table_name}-selection"
  plan_id      = aws_backup_plan.this[0].id
  resources    = [aws_dynamodb_table.this.arn]
}
