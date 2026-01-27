"""
Token Passthrough Lambda for Gateway Interceptor.

This Lambda intercepts Gateway requests and passes through the user's 
inbound JWT token to downstream MCP Runtime targets, enabling user delegation.
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Intercept Gateway request and pass through user's authorization token.
    
    This enables user delegation where MCP Runtime targets receive
    the original user's JWT token for identity-aware tool execution.
    """
    logger.info(f"Token passthrough interceptor received event")
    
    # Extract the gateway request from the MCP structure
    mcp_data = event.get('mcp', {})
    gateway_request = mcp_data.get('gatewayRequest', {})
    headers = gateway_request.get('headers', {})
    body = gateway_request.get('body', {})
    
    logger.info(f"DEBUG: All incoming headers: {json.dumps(headers)}")
    
    logger.info(f"DEBUG: All incoming headers: {json.dumps(headers)}")
    
    # Get the user's inbound authorization token
    # Headers may be lowercase or title-case depending on origin
    auth_header = headers.get('authorization', '') or headers.get('Authorization', '')
    
    if auth_header:
        logger.info("User authorization token found - passing through to target")
    else:
        logger.warning("No authorization header found in request")
    
    # Return transformed request with user's token passed through
    response = {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": {
                    "Authorization": auth_header,
                    "x-amzn-bedrock-agentcore-runtime-user-id": headers.get("x-amzn-bedrock-agentcore-runtime-user-id") or headers.get("X-Amzn-Bedrock-AgentCore-Runtime-User-Id") or "test-user-123", 
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                "body": body
            }
        }
    }
    
    logger.info("Returning transformed request with user token")
    return response
