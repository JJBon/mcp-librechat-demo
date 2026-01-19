################################################################################
# OAuth Metadata API (REST API)
################################################################################

resource "aws_api_gateway_rest_api" "oauth_api" {
  name        = "${var.app_name}-oauth-metadata"
  description = "OAuth 2.1 metadata and DCR endpoints for BedrockAgentCore Gateway"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# /.well-known/openid-configuration
resource "aws_api_gateway_resource" "well_known" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  parent_id   = aws_api_gateway_rest_api.oauth_api.root_resource_id
  path_part   = ".well-known"
}

resource "aws_api_gateway_resource" "oidc_config" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  parent_id   = aws_api_gateway_resource.well_known.id
  path_part   = "openid-configuration"
}

resource "aws_api_gateway_method" "oidc_config_get" {
  rest_api_id   = aws_api_gateway_rest_api.oauth_api.id
  resource_id   = aws_api_gateway_resource.oidc_config.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "oidc_config_mock" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.oidc_config.id
  http_method = aws_api_gateway_method.oidc_config_get.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "oidc_config_200" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.oidc_config.id
  http_method = aws_api_gateway_method.oidc_config_get.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Content-Type"                 = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "oidc_config_response" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.oidc_config.id
  http_method = aws_api_gateway_method.oidc_config_get.http_method
  status_code = aws_api_gateway_method_response.oidc_config_200.status_code

  response_parameters = {
    "method.response.header.Content-Type"                 = "'application/json'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  response_templates = {
    "application/json" = jsonencode({
      issuer                 = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.cognito_user_pool.id}"
      authorization_endpoint = "https://${aws_cognito_user_pool_domain.cognito_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/oauth2/authorize"
      token_endpoint         = "https://${aws_cognito_user_pool_domain.cognito_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/oauth2/token"
      userinfo_endpoint      = "https://${aws_cognito_user_pool_domain.cognito_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/oauth2/userInfo"
      revocation_endpoint    = "https://${aws_cognito_user_pool_domain.cognito_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/oauth2/revoke"
      jwks_uri               = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.cognito_user_pool.id}/.well-known/jwks.json"
      registration_endpoint  = "https://${aws_api_gateway_rest_api.oauth_api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com/prod/register"
      scopes_supported       = ["openid", "email", "phone", "profile", "mcp-unified/read", "mcp-unified/write"],
      response_types_supported = ["code", "token"]
      grant_types_supported    = ["authorization_code", "refresh_token"]
      subject_types_supported  = ["public"]
      id_token_signing_alg_values_supported = ["RS256"]
      token_endpoint_auth_methods_supported = ["client_secret_basic", "client_secret_post"]
      code_challenge_methods_supported      = ["S256"]
    })
  }

  depends_on = [aws_api_gateway_integration.oidc_config_mock]
}

# /register
resource "aws_api_gateway_resource" "register" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  parent_id   = aws_api_gateway_rest_api.oauth_api.root_resource_id
  path_part   = "register"
}

resource "aws_api_gateway_method" "register_post" {
  rest_api_id   = aws_api_gateway_rest_api.oauth_api.id
  resource_id   = aws_api_gateway_resource.register.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "register_lambda" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.register.id
  http_method = aws_api_gateway_method.register_post.http_method
  type        = "AWS_PROXY"
  integration_http_method = "POST"
  uri         = aws_lambda_function.dcr_lambda.invoke_arn
}

# /register OPTIONS (CORS)
resource "aws_api_gateway_method" "register_options" {
  rest_api_id   = aws_api_gateway_rest_api.oauth_api.id
  resource_id   = aws_api_gateway_resource.register.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "register_options_mock" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.register.id
  http_method = aws_api_gateway_method.register_options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "register_options_200" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.register.id
  http_method = aws_api_gateway_method.register_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

resource "aws_api_gateway_integration_response" "register_options_response" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id
  resource_id = aws_api_gateway_resource.register.id
  http_method = aws_api_gateway_method.register_options.http_method
  status_code = aws_api_gateway_method_response.register_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
  }
}


# Deployment
resource "aws_api_gateway_deployment" "oauth_api_deploy" {
  rest_api_id = aws_api_gateway_rest_api.oauth_api.id

  depends_on = [
    aws_api_gateway_integration_response.oidc_config_response,
    aws_api_gateway_integration.register_lambda,
    aws_api_gateway_integration_response.register_options_response
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.oauth_api_deploy.id
  rest_api_id   = aws_api_gateway_rest_api.oauth_api.id
  stage_name    = "prod"
}

################################################################################
# DCR Lambda Function
################################################################################

data "archive_file" "dcr_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/dcr"
  output_path = "${path.module}/dcr.zip"
}

resource "aws_lambda_function" "dcr_lambda" {
  function_name = "${var.app_name}-dcr"
  handler       = "index.handler"
  runtime       = "python3.12"
  role          = aws_iam_role.dcr_lambda_role.arn
  timeout       = 30

  filename         = data.archive_file.dcr_lambda_zip.output_path
  source_code_hash = data.archive_file.dcr_lambda_zip.output_base64sha256

  environment {
    variables = {
      USER_POOL_ID    = aws_cognito_user_pool.cognito_user_pool.id
      GATEWAY_NAME    = "${var.app_name}-Gateway" 
      RESOURCE_PREFIX = var.app_name
      COGNITO_SCOPE   = "mcp-unified/read mcp-unified/write"
    }
  }
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dcr_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.oauth_api.execution_arn}/*/*"
}

################################################################################
# DCR IAM Role
################################################################################

resource "aws_iam_role" "dcr_lambda_role" {
  name = "${var.app_name}-DCRLambdaRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "dcr_basic" {
  role       = aws_iam_role.dcr_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dcr_policy" {
  name = "DCRPolicy"
  role = aws_iam_role.dcr_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:CreateUserPoolClient",
          "cognito-idp:DescribeUserPoolClient"
        ]
        Resource = aws_cognito_user_pool.cognito_user_pool.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:ListGateways",
          "bedrock-agentcore:GetGateway",
          "bedrock-agentcore:UpdateGateway"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = aws_iam_role.agentcore_gateway_role.arn
      }
    ]
  })
}
