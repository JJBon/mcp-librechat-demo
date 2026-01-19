output "gateway_url" {
  description = "MCP Gateway URL for Claude Code"
  value       = aws_bedrockagentcore_gateway.agentcore_gateway.gateway_url
}

output "oauth_metadata_url" {
  description = "OAuth metadata API URL"
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "oidc_config_url" {
  description = "OIDC discovery endpoint"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/.well-known/openid-configuration"
}

output "dcr_endpoint" {
  description = "Dynamic Client Registration endpoint"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/register"
}

output "initial_client_id" {
  description = "Initial Cognito client ID"
  value       = aws_cognito_user_pool_client.cognito_app_client.id
}
