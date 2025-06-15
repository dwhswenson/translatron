variable "project_name" {
  type = string
}

variable "function_name" {
  type = string
}

variable "image_uri" {
  type = string
}

variable "handler_command" {
  type = list(string)
}

variable "environment_vars" {
  type    = map(string)
  default = {}
}

variable "log_retention_days" {
  type    = number
  default = 30
}
