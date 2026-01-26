resource "aws_api_gateway_rest_api" "mock_api" {
  name        = "${var.app_name}-api"
  description = "Mock Target API protected by Cognito (Okta Federated)"
}

# Cognito Authorizer
resource "aws_api_gateway_authorizer" "cognito_auth" {
  name          = "CognitoAuthorizer"
  type          = "COGNITO_USER_POOLS"
  rest_api_id   = aws_api_gateway_rest_api.mock_api.id
  provider_arns = [aws_cognito_user_pool.mock_pool.arn]
}

# /data Resource
resource "aws_api_gateway_resource" "data" {
  rest_api_id = aws_api_gateway_rest_api.mock_api.id
  parent_id   = aws_api_gateway_rest_api.mock_api.root_resource_id
  path_part   = "data"
}

# GET /data Method (Protected)
resource "aws_api_gateway_method" "get_data" {
  rest_api_id   = aws_api_gateway_rest_api.mock_api.id
  resource_id   = aws_api_gateway_resource.data.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito_auth.id
}

# Mock Integration
resource "aws_api_gateway_integration" "mock_integration" {
  rest_api_id = aws_api_gateway_rest_api.mock_api.id
  resource_id = aws_api_gateway_resource.data.id
  http_method = aws_api_gateway_method.get_data.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "response_200" {
  rest_api_id = aws_api_gateway_rest_api.mock_api.id
  resource_id = aws_api_gateway_resource.data.id
  http_method = aws_api_gateway_method.get_data.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "mock_response" {
  rest_api_id = aws_api_gateway_rest_api.mock_api.id
  resource_id = aws_api_gateway_resource.data.id
  http_method = aws_api_gateway_method.get_data.http_method
  status_code = aws_api_gateway_method_response.response_200.status_code

  response_templates = {
    "application/json" = <<EOF
{
  "message": "Hello via 3LO!",
  "status": "success",
  "data": {
    "id": 123,
    "value": "This data is protected by Cognito/Okta"
  }
}
EOF
  }
}

# Deployment
resource "aws_api_gateway_deployment" "deployment" {
  rest_api_id = aws_api_gateway_rest_api.mock_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.data.id,
      aws_api_gateway_method.get_data.id,
      aws_api_gateway_integration.mock_integration.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.deployment.id
  rest_api_id   = aws_api_gateway_rest_api.mock_api.id
  stage_name    = "prod"
}
