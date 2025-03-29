variable "project_name" {
  description = "Base name for all resources"
  type        = string
}

variable "lambda_role_name" {
  description = "Name of the IAM role to attach this policy to"
  type        = string
}
