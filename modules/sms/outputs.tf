output "sms_lambda_function_name" {
  value = aws_lambda_function.sms_handler.function_name
}

output "sms_function_url" {
  description = "The Lambda Function URL for SMS processing"
  value       = aws_lambda_function_url.sms_function_url.function_url
}

output "sms_dynamodb_table" {
  value = aws_dynamodb_table.sms_messages.name
}

output "sms_lambda_role_name" {
  description = "Name of the IAM role for the SMS Lambda"
  value       = aws_iam_role.sms_lambda_role.name
}
