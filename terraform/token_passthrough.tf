################################################################################
# Token Passthrough Lambda for Gateway Interceptor
# 
# This Lambda intercepts requests to MCP Runtime targets and passes 
# through the user's JWT token for user delegation.
################################################################################

data "archive_file" "token_passthrough_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/token_passthrough/"
  output_path = "${path.module}/token_passthrough_lambda.zip"
}

resource "aws_lambda_function" "token_passthrough_lambda" {
  function_name = "${var.app_name}-TokenPassthroughLambda"
  role          = aws_iam_role.token_passthrough_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"

  filename         = data.archive_file.token_passthrough_lambda_zip.output_path
  source_code_hash = data.archive_file.token_passthrough_lambda_zip.output_base64sha256

  timeout     = 30
  memory_size = 128

  depends_on = [aws_cloudwatch_log_group.token_passthrough_lambda_logs]
}

resource "aws_cloudwatch_log_group" "token_passthrough_lambda_logs" {
  name              = "/aws/lambda/${var.app_name}-TokenPassthroughLambda"
  retention_in_days = 7
}

resource "aws_iam_role" "token_passthrough_lambda_role" {
  name = "${var.app_name}-TokenPassthroughLambdaRole"

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

resource "aws_iam_role_policy_attachment" "token_passthrough_lambda_basic" {
  role       = aws_iam_role.token_passthrough_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
