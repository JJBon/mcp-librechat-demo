output "api_endpoint" {
  value = "${aws_api_gateway_stage.prod.invoke_url}/data"
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.mock_pool.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.mock_client.id
}

output "cognito_domain" {
  value = "https://${aws_cognito_user_pool_domain.mock_domain.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_redirect_uri" {
  value = "https://${aws_cognito_user_pool_domain.mock_domain.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/idpresponse"
}

output "cognito_client_secret" {
  value     = aws_cognito_user_pool_client.mock_client.client_secret
  sensitive = true
}
