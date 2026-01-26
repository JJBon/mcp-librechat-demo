resource "aws_cognito_user_pool" "mock_pool" {
  name = "${var.app_name}-user-pool"

  # Minimal settings for testing
  password_policy {
    minimum_length    = 8
    require_lowercase = false
    require_numbers   = false
    require_symbols   = false
    require_uppercase = false
  }

  # Attributes
  auto_verified_attributes = ["email"]
  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true
  }
}

resource "aws_cognito_user_pool_domain" "mock_domain" {
  domain       = "${var.app_name}-${random_string.suffix.result}"
  user_pool_id = aws_cognito_user_pool.mock_pool.id
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Configure Okta as an Upstream IdP
resource "aws_cognito_identity_provider" "okta_provider" {
  user_pool_id  = aws_cognito_user_pool.mock_pool.id
  provider_name = "Okta"
  provider_type = "OIDC"

  provider_details = {
    authorize_scopes          = "openid profile email"
    client_id                 = var.okta_client_id
    client_secret             = var.okta_client_secret
    attributes_request_method = "GET"
    oidc_issuer               = var.okta_issuer
    authorize_url             = "${var.okta_issuer}/v1/authorize"
    token_url                 = "${var.okta_issuer}/v1/token"
    attributes_url            = "${var.okta_issuer}/v1/userinfo"
    jwks_uri                  = "${var.okta_issuer}/v1/keys"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

resource "aws_cognito_user_pool_client" "mock_client" {
  name         = "${var.app_name}-client"
  user_pool_id = aws_cognito_user_pool.mock_pool.id

  # OAuth Configuration
  generate_secret = true

  # Allow both Cognito Native users and Okta Federated users
  supported_identity_providers = ["COGNITO", "Okta"]

  callback_urls = [
    "https://oauth.pstmn.io/v1/callback", # Postman for testing
    "http://localhost:3000/callback"      # Local dev
  ]

  logout_urls = [
    "http://localhost:3000/logout"
  ]

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  depends_on = [aws_cognito_identity_provider.okta_provider]
}
