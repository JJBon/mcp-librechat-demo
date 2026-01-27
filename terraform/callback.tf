################################################################################
# Callback API (REST API) for 3LO
################################################################################

resource "aws_api_gateway_rest_api" "callback_api" {
  name        = "${var.app_name}-callback-api"
  description = "OAuth 2.1 Callback Endpoint for AgentCore 3LO"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "callback_resource" {
  rest_api_id = aws_api_gateway_rest_api.callback_api.id
  parent_id   = aws_api_gateway_rest_api.callback_api.root_resource_id
  path_part   = "callback"
}

resource "aws_api_gateway_method" "callback_get" {
  rest_api_id   = aws_api_gateway_rest_api.callback_api.id
  resource_id   = aws_api_gateway_resource.callback_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "callback_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.callback_api.id
  resource_id             = aws_api_gateway_resource.callback_resource.id
  http_method             = aws_api_gateway_method.callback_get.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.callback_lambda.invoke_arn
}

resource "aws_api_gateway_method_response" "callback_200" {
  rest_api_id = aws_api_gateway_rest_api.callback_api.id
  resource_id = aws_api_gateway_resource.callback_resource.id
  http_method = aws_api_gateway_method.callback_get.http_method
  status_code = "200"
}

resource "aws_api_gateway_deployment" "callback_deploy" {
  rest_api_id = aws_api_gateway_rest_api.callback_api.id
  depends_on  = [aws_api_gateway_integration.callback_lambda_integration]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "callback_prod" {
  deployment_id = aws_api_gateway_deployment.callback_deploy.id
  rest_api_id   = aws_api_gateway_rest_api.callback_api.id
  stage_name    = "prod"
}

################################################################################
# Callback Lambda Function
################################################################################

# Reuse the DCR build pattern or creating a new one? 
# For simplicity, we'll try to package it simply or reuse the build dir approach if needed.
# Since we have specific requirements (bedrock-agentcore), we might need a layer or build.
# We'll use a zip archive for now.

data "archive_file" "callback_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/callback"
  output_path = "${path.module}/callback.zip"
  excludes    = ["requirements.txt", "__pycache__"]
}

resource "aws_lambda_function" "callback_lambda" {
  function_name = "${var.app_name}-callback"
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.callback_lambda_role.arn
  timeout       = 30

  filename         = data.archive_file.callback_lambda_zip.output_path
  source_code_hash = data.archive_file.callback_lambda_zip.output_base64sha256

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }
}

resource "aws_lambda_permission" "callback_apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvokeCallback"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.callback_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.callback_api.execution_arn}/*/*"
}

################################################################################
# Callback IAM Role
################################################################################

resource "aws_iam_role" "callback_lambda_role" {
  name = "${var.app_name}-CallbackLambdaRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "callback_basic" {
  role       = aws_iam_role.callback_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy to allow calling Bedrock/Identity APIs
resource "aws_iam_role_policy" "callback_policy" {
  name = "CallbackPolicy"
  role = aws_iam_role.callback_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agent-runtime:*",
          "bedrock:*",
          "bedrock-agentcore:*" # Assuming this is the placeholder for the new service
        ]
        Resource = "*"
      }
    ]
  })
}

output "callback_url" {
  value       = "${aws_api_gateway_stage.callback_prod.invoke_url}/callback"
  description = "The public URL to register in Okta and AgentCore Identity"
}
