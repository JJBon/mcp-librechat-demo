################################################################################
# Syntheticdata OAuth Credential Provider
# 
# M2M OAuth for Gateway to authenticate with Syntheticdata Runtime.
# User identity is passed through via the gateway interceptor.
################################################################################

# Variables for Okta M2M authentication for syntheticdata Runtime

# Create OAuth2 credential provider for Okta (CustomOauth2)
resource "aws_bedrockagentcore_oauth2_credential_provider" "syntheticdata_oauth" {
  count = var.syntheticdata_runtime_arn != "" && var.syntheticdata_okta_client_id != "" ? 1 : 0

  name                       = "${var.app_name}-syntheticdata-oauth-provider"
  credential_provider_vendor = "CustomOauth2"

  oauth2_provider_config {
    custom_oauth2_provider_config {
      oauth_discovery {
        discovery_url = "https://${var.okta_domain}/oauth2/default/.well-known/openid-configuration"
      }
      client_id     = var.syntheticdata_okta_client_id
      client_secret = var.syntheticdata_okta_client_secret
    }
  }
}
