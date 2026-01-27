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

################################################################################
# Optional MCP Runtime Targets
################################################################################

variable "syntheticdata_runtime_arn" {
  description = "ARN of the syntheticdata MCP server deployed to AgentCore Runtime. Leave empty to skip this target. Deploy using runtime/syntheticdata/deploy_runtime.py first."
  type        = string
  default     = ""
}

variable "syntheticdata_okta_client_id" {
  description = "Client ID for Synthetic Data M2M App"
  type        = string
  default     = ""
}

variable "syntheticdata_okta_client_secret" {
  description = "Client Secret for Synthetic Data M2M App"
  type        = string
  sensitive   = true
  default     = ""
}

variable "syntheticdata_okta_scope" {
  description = "Scope for Synthetic Data M2M App"
  type        = string
  default     = "syntheticdata:invoke"
}

variable "okta_3lo_client_id" {
  description = "Client ID for Okta 3LO App"
  type        = string
  default     = ""
}

variable "okta_3lo_client_secret" {
  description = "Client Secret for Okta 3LO App"
  type        = string
  sensitive   = true
  default     = ""
}
