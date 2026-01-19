import json
import os
import re
import boto3
import uuid
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito = boto3.client('cognito-idp')
agentcore = boto3.client('bedrock-agentcore-control')

def find_gateway_by_name(name):
    """Find gateway ID by name to avoid circular CloudFormation dependency"""
    try:
        paginator = agentcore.get_paginator('list_gateways')
        for page in paginator.paginate():
            # IMPORTANT: API returns 'items', not 'gateways'
            for gw in page.get('items', []):
                if gw.get('name') == name:
                    return gw.get('gatewayId')
    except Exception as e:
        logger.error(f"Failed to find gateway: {e}")
    return None

def handler(event, context):
    logger.info(f"DCR request: {json.dumps(event)}")

    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return response(400, {'error': 'invalid_request', 'error_description': 'Invalid JSON body'})

    # Extract client metadata
    raw_client_name = body.get('client_name', f"dcr-client-{uuid.uuid4().hex[:8]}")

    # CRITICAL: Sanitize client name
    # Cognito only allows [\w\s+=,.@-]+
    # Claude Code sends names like "Claude Code (server-name)" which contain parentheses
    client_name = re.sub(r'[^\w\s+=,.@-]', '-', raw_client_name)

    redirect_uris = body.get('redirect_uris', ['http://127.0.0.1:33418', 'http://localhost:33418'])

    # Validate redirect URIs
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return response(400, {'error': 'invalid_redirect_uri', 'error_description': 'redirect_uris must be a non-empty array'})

    user_pool_id = os.environ['USER_POOL_ID']
    gateway_name = os.environ['GATEWAY_NAME']
    prefix = os.environ['RESOURCE_PREFIX']

    try:
        # Create Cognito client with OAuth configuration
        client_response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=client_name,
            GenerateSecret=True,
            ExplicitAuthFlows=['ALLOW_USER_SRP_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH'],
            AllowedOAuthFlows=['code'],
            AllowedOAuthScopes=os.environ['COGNITO_SCOPE'].split(' ') + ['email', 'openid', 'phone', 'profile'],
            AllowedOAuthFlowsUserPoolClient=True,
            CallbackURLs=redirect_uris,
            SupportedIdentityProviders=['COGNITO']
        )

        client_id = client_response['UserPoolClient']['ClientId']
        client_secret = client_response['UserPoolClient']['ClientSecret']

        logger.info(f"Created Cognito client: {client_id} (name: {client_name})")

        # Add client to gateway AllowedClients
        gateway_id = find_gateway_by_name(gateway_name)
        if gateway_id:
            try:
                gateway = agentcore.get_gateway(gatewayIdentifier=gateway_id)

                current_clients = gateway.get('authorizerConfiguration', {}).get('customJWTAuthorizer', {}).get('allowedClients', [])
                updated_clients = list(set(current_clients + [client_id]))

                agentcore.update_gateway(
                    gatewayIdentifier=gateway_id,
                    name=gateway['name'],
                    roleArn=gateway['roleArn'],
                    protocolType=gateway['protocolType'],
                    authorizerType=gateway['authorizerType'],
                    authorizerConfiguration={
                        'customJWTAuthorizer': {
                            'discoveryUrl': gateway['authorizerConfiguration']['customJWTAuthorizer']['discoveryUrl'],
                            'allowedClients': updated_clients
                        }
                    }
                )
                logger.info(f"Added client {client_id} to gateway AllowedClients")
            except Exception as e:
                logger.error(f"Failed to update gateway: {e}")
                # Don't fail the request - client is created, just needs manual gateway update
        else:
            logger.warning(f"Gateway '{gateway_name}' not found - client created but not added to AllowedClients")

        # Return RFC 7591 compliant response
        return response(201, {
            'client_id': client_id,
            'client_secret': client_secret,
            'client_name': client_name,
            'redirect_uris': redirect_uris,
            'token_endpoint_auth_method': 'client_secret_basic',
            'grant_types': ['authorization_code', 'refresh_token'],
            'response_types': ['code']
        })

    except cognito.exceptions.InvalidParameterException as e:
        logger.error(f"Invalid parameter: {e}")
        return response(400, {'error': 'invalid_request', 'error_description': str(e)})
    except Exception as e:
        logger.error(f"DCR failed: {e}")
        return response(500, {'error': 'server_error', 'error_description': 'Client registration failed'})

def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps(body)
    }
