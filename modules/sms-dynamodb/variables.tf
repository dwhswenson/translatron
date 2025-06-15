variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "table_name" {
  type = string
}

variable "lambda_role_name" {
  type = string
}

variable "backup_vault_name" {
  type    = string
  default = null
}

variable "backup_plan_schedule" {
  type    = string
  default = "cron(0 5 * * ? *)"
}

variable "backup_retention_days" {
  type    = number
  default = 30
}
