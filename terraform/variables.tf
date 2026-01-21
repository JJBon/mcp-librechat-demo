variable "app_name" {
  description = "Application name"
  type        = string
}

variable "agent_runtime_version" {
  description = "Runtime version for PROD endpoint"
  type        = string
  default     = "1"
}

variable "okta_domain" {
  description = "Okta Domain (e.g., dev-12345.okta.com)"
  type        = string
}

variable "okta_client_id" {
  description = "Okta Service App Client ID"
  type        = string
}

variable "okta_client_secret" {
  description = "Okta Service App Client Secret"
  type        = string
  sensitive   = true
}

variable "okta_app_group_id" {
  description = "Okta Group ID for AgentCore Apps (defines the Admin Role Resource Set scope)"
  type        = string
}

data "aws_region" "current" { }

data "aws_caller_identity" "current" {}
