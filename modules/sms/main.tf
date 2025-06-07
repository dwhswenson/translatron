# Create an IAM Role for the SMS Lambda function
resource "aws_iam_role" "sms_lambda_role" {
  name = "${var.project_name}-sms-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "sms_dynamodb_policy" {
  name = "${var.project_name}-sms-dynamodb-policy"
  role = aws_iam_role.sms_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ]
      Resource = aws_dynamodb_table.sms_messages.arn
    }]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_policy_attachment" "sms_lambda_policy_attach" {
  name       = "${var.project_name}-sms-lambda-policy-attach"
  roles      = [aws_iam_role.sms_lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Create a DynamoDB table for SMS messages
resource "aws_dynamodb_table" "sms_messages" {
  name         = var.dynamodb_sms_table_name
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

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}


# DynamoDB backups
resource "aws_backup_vault" "dynamo_backup_vault" {
  name = "sms-dynamo-backup-vault"
}


resource "aws_backup_plan" "dynamo_backup_plan" {
  name = "sms-dynamo-backup-plan"

  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.dynamo_backup_vault.name
    schedule          = "cron(0 5 * * ? *)" # Daily at 5 AM UTC
    lifecycle {
      delete_after = 30 # Retain backups for 30 days
    }
  }
}

resource "aws_iam_role" "backup_role" {
  name = "aws-backup-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_backup_selection" "dynamo_backup_selection" {
  iam_role_arn = aws_iam_role.backup_role.arn
  name         = "sms-dynamo-backup-selection"
  plan_id      = aws_backup_plan.dynamo_backup_plan.id

  resources = [
    aws_dynamodb_table.sms_messages.arn
  ]
}


# Create the Lambda function for SMS processing
resource "aws_lambda_function" "sms_handler" {
  function_name = "${var.project_name}-sms-handler"
  package_type  = "Image"
  image_uri     = var.lambda_container_image_uri
  role          = aws_iam_role.sms_lambda_role.arn

  image_config {
    # Override the default CMD to point to the SMS handler function
    command = [var.sms_handler_handler]
  }

  timeout = 60

  environment {
    variables = {
      DYNAMODB_TABLE      = aws_dynamodb_table.sms_messages.name
      TRANSLATOR_PROVIDER = "amazon" # TODO make variable
      TARGET_LANGUAGES    = "en,fa"  # TODO make variable (or get from user_info?)
      # Additional environment variables as needed (e.g., translation API keys)
      # temporary twilio testing
      USER_INFO          = var.user_info
      TEST_PHONE         = var.test_phone
      TWILIO_ACCOUNT_SID = var.twilio_account_sid
      TWILIO_AUTH_TOKEN  = var.twilio_auth_token
      TWILIO_NUMBER      = var.twilio_phone_number
      DEV_VERSION        = var.dev_version
    }
  }
}

# Create a Lambda Function URL for the SMS function
resource "aws_lambda_function_url" "sms_function_url" {
  function_name      = aws_lambda_function.sms_handler.function_name
  authorization_type = "NONE" # Allow public access
  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
  }
}

resource "aws_lambda_permission" "allow_all" {
  statement_id           = "AllowPublicInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.sms_handler.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
