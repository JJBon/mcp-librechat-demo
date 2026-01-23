locals {
  # Adjust path to src directory relative to this module
  # mcplibrechatdemo is in agencore_demo/, src is in agencore_demo/src
  src_dir = "${path.module}/../agentMcp/src"

  src_files = fileset(local.src_dir, "**")
  src_hashes = [
    for f in local.src_files :
    filesha256("${local.src_dir}/${f}")
  ]

  # Collapse all file hashes into one
  src_hash = sha256(join("", local.src_hashes))
}



################################################################################
# MCP Lambda Function (Backend)
################################################################################
data "archive_file" "mcp_lambda_zip" {
  type = "zip"
  # Use the built directory with dependencies
  source_dir  = "${path.module}/../lambda/mcp/"
  output_path = "${path.module}/mcp_lambda.zip"
}

resource "aws_lambda_function" "mcp_lambda" {
  function_name = "${var.app_name}-McpLambda"
  role          = aws_iam_role.mcp_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"

  filename         = data.archive_file.mcp_lambda_zip.output_path
  source_code_hash = data.archive_file.mcp_lambda_zip.output_base64sha256

  depends_on = [aws_cloudwatch_log_group.mcp_lambda_logs]
}

resource "aws_cloudwatch_log_group" "mcp_lambda_logs" {
  name              = "/aws/lambda/${var.app_name}-McpLambda"
  retention_in_days = 7
}

resource "aws_iam_role" "mcp_lambda_role" {
  name = "${var.app_name}-McpLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "mcp_lambda_basic" {
  role       = aws_iam_role.mcp_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

################################################################################
# AgentCore Gateway Roles
################################################################################

resource "aws_iam_role" "agentcore_gateway_role" {
  name = "${var.app_name}-AgentCoreGatewayRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = [
          "bedrock.amazonaws.com",
          "bedrock-agentcore.amazonaws.com"
        ]
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "agentcore_gateway_permissions" {
  role       = aws_iam_role.agentcore_gateway_role.name
  policy_arn = "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
}

resource "aws_iam_role_policy" "agentcore_gateway_lambda_invoke" {
  role = aws_iam_role.agentcore_gateway_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["lambda:InvokeFunction"]
      Effect   = "Allow"
      Resource = [aws_lambda_function.mcp_lambda.arn]
    }]
  })
}

################################################################################
# AgentCore Gateway
################################################################################

resource "aws_bedrockagentcore_gateway" "agentcore_gateway" {
  name            = "${var.app_name}-Gateway"
  protocol_type   = "MCP"
  role_arn        = aws_iam_role.agentcore_gateway_role.arn
  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration {
    custom_jwt_authorizer {
      # Use the DCR API Gateway OIDC endpoint NOT the Cognito one directly
      discovery_url = "${aws_api_gateway_stage.prod.invoke_url}/.well-known/openid-configuration"
      # Typically empty initially for DCR, or add a manual static client ID if you have one.
      allowed_clients = ["placeholder-client-id"]
    }
  }
}

resource "aws_bedrockagentcore_gateway_target" "agentcore_gateway_lambda_target" {
  name               = "${var.app_name}-Target"
  gateway_identifier = aws_bedrockagentcore_gateway.agentcore_gateway.gateway_id

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.mcp_lambda.arn

        tool_schema {
          inline_payload {
            name        = "add_numbers"
            description = "Add two numbers together"
            input_schema {
              type = "object"
              property {
                name        = "a"
                type        = "integer"
                description = "First number"
              }
              property {
                name        = "b"
                type        = "integer"
                description = "Second number"
              }
            }
          }
          inline_payload {
            name        = "multiply_numbers"
            description = "Multiply two numbers together"
            input_schema {
              type = "object"
              property {
                name        = "a"
                type        = "integer"
                description = "First number"
              }
              property {
                name        = "b"
                type        = "integer"
                description = "Second number"
              }
            }
          }
          inline_payload {
            name        = "greet_user"
            description = "Greet a user by name"
            input_schema {
              type = "object"
              property {
                name        = "name"
                type        = "string"
                description = "User name"
              }
            }
          }
        }
      }
    }
  }
}

