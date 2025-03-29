output "voice_lambda_function_name" {
  value = aws_lambda_function.voice_handler.function_name
}

output "voice_function_url" {
  description = "The Lambda Function URL for Voice processing"
  value       = aws_lambda_function_url.voice_function_url.function_url
}

output "voice_dynamodb_table" {
  value = aws_dynamodb_table.voice_messages.name
}

output "voicemail_bucket" {
  value = aws_s3_bucket.voicemail_bucket.bucket
}
