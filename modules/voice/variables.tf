variable "project_name" {
  description = "The project name used for naming resources."
  type        = string
}

variable "environment" {
  description = "The deployment environment (e.g., production, staging)."
  type        = string
}

variable "dynamodb_voice_table_name" {
  description = "Name for the DynamoDB table to store Voice messages."
  type        = string
}

variable "voicemail_bucket_name" {
  description = "Name for the S3 bucket to store voicemail recordings."
  type        = string
}

variable "lambda_container_image_uri" {
  description = "The ECR image URI for the Lambda functions."
  type        = string
}

variable "voice_handler_handler" {
  description = "The handler for the Voice Lambda function (e.g., voice_handler.lambda_handler)."
  type        = string
}
