variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "mock-3lo-target"
}

variable "okta_issuer" {
  description = "Okta OIDC Issuer URL (e.g. https://dev-123456.okta.com)"
  type        = string
}

variable "okta_client_id" {
  description = "Client ID for the Okta App Integration used by Cognito"
  type        = string
}

variable "okta_client_secret" {
  description = "Client Secret for the Okta App Integration used by Cognito"
  type        = string
  sensitive   = true
}
