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

variable "okta_private_key_id" {
  description = "Key ID (kid) for the Private Key"
  type        = string
}

variable "okta_app_group_id" {
  description = "Okta Group ID for AgentCore Apps (optional - for app assignment)"
  type        = string
  default     = ""
}

variable "allow_localhost_dcr" {
  description = "Allow 'localhost' or '127.0.0.1' in redirect URIs (Set to false for Production)"
  type        = bool
  default     = false
}

variable "allowed_redirect_domain_pattern" {
  description = "Regex pattern for allowed domains (e.g., '.*\\.corp\\.com'). Empty allows all."
  type        = string
  default     = ""
}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

variable "okta_private_key_secret_name" {
  description = "Name or ARN of the AWS Secrets Manager secret containing the Okta private key PEM"
  type        = string
}

variable "okta_private_key_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret (for IAM policy)"
  type        = string
}
