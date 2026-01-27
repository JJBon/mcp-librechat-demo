################################################################################
# Okta 3LO (Authorization Code) OAuth Credential Provider
# 
# Used by Agents (@requires_access_token) to request user authorization
# via the "User Federation" flow.
################################################################################


resource "aws_bedrockagentcore_oauth2_credential_provider" "okta_3lo_provider" {
  count = var.okta_3lo_client_id != "" ? 1 : 0

  name                       = "${var.app_name}-okta-3lo-provider"
  credential_provider_vendor = "CustomOauth2"

  oauth2_provider_config {
    custom_oauth2_provider_config {
      oauth_discovery {
        discovery_url = "https://${var.okta_domain}/oauth2/default/.well-known/openid-configuration"
      }
      client_id     = var.okta_3lo_client_id
      client_secret = var.okta_3lo_client_secret
    }
  }
}
