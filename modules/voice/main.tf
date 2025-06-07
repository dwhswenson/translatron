# Create an IAM Role for the Voice Lambda function
resource "aws_iam_role" "voice_lambda_role" {
  name = "${var.project_name}-voice-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_policy_attachment" "voice_lambda_policy_attach" {
  name       = "${var.project_name}-voice-lambda-policy-attach"
  roles      = [aws_iam_role.voice_lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Create a DynamoDB table for Voice messages
resource "aws_dynamodb_table" "voice_messages" {
  name         = var.dynamodb_voice_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  attribute {
    name = "caller"
    type = "S"
  }

  global_secondary_index {
    name            = "CallerIndex"
    hash_key        = "caller"
    projection_type = "ALL"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create an S3 bucket for voicemail recordings
resource "aws_s3_bucket" "voicemail_bucket" {
  bucket = var.voicemail_bucket_name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "voice_handler" {
  function_name = "${var.project_name}-voice-handler"
  package_type  = "Image"
  image_uri     = var.lambda_container_image_uri
  role          = aws_iam_role.voice_lambda_role.arn

  image_config {
    # Override the default CMD to point to the Voice handler function
    command = [var.voice_handler_handler]
  }

  environment {
    variables = {
      DYNAMODB_TABLE   = aws_dynamodb_table.voice_messages.name
      VOICEMAIL_BUCKET = aws_s3_bucket.voicemail_bucket.bucket
      # Additional environment variables as needed (e.g., transcription API keys)
    }
  }
}

# Create a Lambda Function URL for the Voice function
resource "aws_lambda_function_url" "voice_function_url" {
  function_name      = aws_lambda_function.voice_handler.function_name
  authorization_type = "NONE" # Consider using AWS_IAM for additional security
  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
  }
}
