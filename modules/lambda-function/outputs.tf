output "lambda_role_name" {
  value = aws_iam_role.this.name
}

output "lambda_role_arn" {
  value = aws_iam_role.this.arn
}

output "function_url" {
  value = aws_lambda_function_url.this.function_url
}
