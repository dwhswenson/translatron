variable "user_info" {
  description = "The user information, JSON-endcoded"
  type        = string
}

variable "twilio_phone_number" {
  description = "The Twilio phone number to send SMS messages to/from."
  type        = string
}

variable "twilio_account_sid" {
  description = "The Twilio account SID."
  type        = string
}

variable "twilio_auth_token" {
  description = "The Twilio auth token."
  type        = string
}

variable "test_phone" {
  description = "The phone number to send test SMS messages to."
  type        = string
}

variable "project_name" {
  description = "The project name used for naming resources."
  type        = string
}

variable "environment" {
  description = "The deployment environment (e.g., production, staging)."
  type        = string
}

variable "dynamodb_sms_table_name" {
  description = "Name for the DynamoDB table to store SMS messages."
  type        = string
}

# For container-based Lambdas, we use a shared image URI.
variable "lambda_container_image_uri" {
  description = "The ECR image URI for the Lambda functions."
  type        = string
}

variable "sms_handler_handler" {
  description = "The handler for the SMS Lambda function (e.g., sms_handler.lambda_handler)."
  type        = string
}
