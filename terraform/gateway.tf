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

  # Syntheticdata MCP Server Target (Optional)
  # Construct the runtime invocation URL with URL-encoded ARN
  syntheticdata_encoded_arn = var.syntheticdata_runtime_arn != "" ? replace(replace(var.syntheticdata_runtime_arn, ":", "%3A"), "/", "%2F") : ""
  syntheticdata_endpoint    = var.syntheticdata_runtime_arn != "" ? "https://bedrock-agentcore.${data.aws_region.current.name}.amazonaws.com/runtimes/${local.syntheticdata_encoded_arn}/invocations?qualifier=DEFAULT" : ""
}

################################################################################
# Syntheticdata MCP Server Target (Optional)
# Deploy runtime first: runtime/syntheticdata/deploy_runtime.py
# Then set syntheticdata_runtime_arn variable
################################################################################


resource "aws_iam_role_policy" "agentcore_gateway_syntheticdata_invoke" {
  count = var.syntheticdata_runtime_arn != "" ? 1 : 0

  role = aws_iam_role.agentcore_gateway_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "bedrock-agentcore:InvokeRuntime",
        "bedrock-agentcore:InvokeRuntimeWithResponseStream"
      ]
      Effect   = "Allow"
      Resource = [var.syntheticdata_runtime_arn]
    }]
  })
}
# Note: MCP Runtime targets require OAuth credential provider for M2M auth.
# Gateway authenticates to Runtime using client_credentials.
# User identity is passed through via the interceptor for authorization.
resource "aws_bedrockagentcore_gateway_target" "syntheticdata_target" {
  count = var.syntheticdata_runtime_arn != "" && var.syntheticdata_okta_client_id != "" ? 1 : 0

  name               = "${var.app_name}-SyntheticData-Target-v8"
  gateway_identifier = aws_bedrockagentcore_gateway.agentcore_gateway.gateway_id

  # M2M OAuth for Gateway → Runtime connectivity
  credential_provider_configuration {
    oauth {
      provider_arn = aws_bedrockagentcore_oauth2_credential_provider.syntheticdata_oauth[0].credential_provider_arn
      scopes       = [var.syntheticdata_okta_scope]
    }
  }

  target_configuration {
    mcp {
      mcp_server {
        endpoint = local.syntheticdata_endpoint
      }
    }
  }

  depends_on = [
    aws_bedrockagentcore_gateway.agentcore_gateway,
    aws_bedrockagentcore_oauth2_credential_provider.syntheticdata_oauth
  ]
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
      Action = ["lambda:InvokeFunction"]
      Effect = "Allow"
      Resource = [
        aws_lambda_function.mcp_lambda.arn,
        aws_lambda_function.token_passthrough_lambda.arn
      ]
    }]
  })
}

################################################################################
# AgentCore Gateway
################################################################################

resource "aws_bedrockagentcore_gateway" "agentcore_gateway" {
  name          = "${var.app_name}-Gateway"
  protocol_type = "MCP"
  protocol_configuration {
    mcp {
      instructions       = "Gateway for handling MCP requests"
      search_type        = "SEMANTIC"
      supported_versions = ["2025-06-18"]
    }
  }
  role_arn        = aws_iam_role.agentcore_gateway_role.arn
  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration {
    custom_jwt_authorizer {
      # Point directly to real Okta (skip DCR proxy for validation reliability)
      discovery_url = "${aws_api_gateway_stage.prod.invoke_url}/.well-known/openid-configuration"

      allowed_clients = ["placeholder-client-id"]
    }
  }

  # Interceptor for token passthrough to MCP Runtime targets
  # Passes user's JWT to Runtime for user delegation
  interceptor_configuration {
    interceptor {
      lambda {
        arn = aws_lambda_function.token_passthrough_lambda.arn
      }
    }
    interception_points = ["REQUEST"]
    input_configuration {
      pass_request_headers = true
    }
  }

  lifecycle {
    ignore_changes = [
      authorizer_configuration
    ]
  }

  depends_on = [aws_lambda_function.token_passthrough_lambda]
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

