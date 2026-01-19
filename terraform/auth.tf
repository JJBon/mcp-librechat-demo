################################################################################
# AgentCore Gateway Inbound Auth - Cognito
################################################################################

resource "aws_cognito_user_pool" "cognito_user_pool" {
  name = "${var.app_name}-CognitoUserPool"
}

resource "aws_cognito_resource_server" "cognito_resource_server" {
  identifier   = "mcp-unified"
  name         = "${var.app_name}-CognitoResourceServer"
  user_pool_id = aws_cognito_user_pool.cognito_user_pool.id
  scope {
    scope_description = "Read access to ${var.app_name}"
    scope_name        = "read"
  }
  scope {
    scope_description = "Write access to ${var.app_name}"
    scope_name        = "write"
  }
}

resource "aws_cognito_user_pool_client" "cognito_app_client" {
  name                                 = "${var.app_name}-CognitoUserPoolClient"
  user_pool_id                         = aws_cognito_user_pool.cognito_user_pool.id
  generate_secret                      = true
  # DCR requires these flows for the initial/manual client too if we want parity
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"] 
  allowed_oauth_flows                  = ["code"] # Removed client_credentials to avoid conflict
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["mcp-unified/read", "mcp-unified/write", "email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["http://127.0.0.1:33418", "http://localhost:33418", "http://localhost:3080/oauth/callback"]
  depends_on                           = [aws_cognito_resource_server.cognito_resource_server]
}

resource "aws_cognito_user_pool_domain" "cognito_domain" {
  domain       = "${lower(var.app_name)}-${data.aws_region.current.region}"
  user_pool_id = aws_cognito_user_pool.cognito_user_pool.id
}
