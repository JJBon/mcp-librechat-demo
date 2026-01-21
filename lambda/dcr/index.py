import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse
import boto3
import uuid
import logging
import base64
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def get_okta_token(okta_domain, client_id, client_secret):
    """Fetches an OAuth 2.0 Access Token from Okta using Client Credentials"""
    url = f"https://{okta_domain}/oauth2/v1/token"
    
    # HTTP Basic Auth header
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {b64_auth}'
    }
    
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'scope': 'okta.clients.manage okta.groups.appAssignment.manage' # Request necessary scopes
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            token_data = json.loads(response.read().decode('utf-8'))
            return token_data.get('access_token')
    except Exception as e:
        logger.error(f"Failed to get Okta access token: {e}")
        raise Exception("Authentication with Okta failed")

def assign_app_to_group(app_id, group_id, api_token, okta_domain):
    """Assigns the newly created Okta App to the AgentCore Group (for scoped administration)"""
    url = f"https://{okta_domain}/api/v1/apps/{app_id}/groups/{group_id}"
    
    # PUT request to assign group
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_token}'
    }
    
    try:
        # Empty body for this PUT request
        req = urllib.request.Request(url, data=json.dumps({}).encode('utf-8'), headers=headers, method='PUT')
        with urllib.request.urlopen(req) as response:
            logger.info(f"Assigned app {app_id} to group {group_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to assign app {app_id} to group {group_id}: {e}")
        # We don't raise here because the app is already created; we just log the error.
        # However, this leaves the app "orphaned" from the Admin's perspective if using Scoped Roles.
        return False

def create_okta_client(client_name, redirect_uris, api_token, okta_domain):
    """Creates an OIDC App in Okta"""
    url = f"https://{okta_domain}/api/v1/apps"
    
    # Payload for creating an OIDC app
    payload = {
        "name": "oidc_client",
        "label": client_name,
        "signOnMode": "OPENID_CONNECT",
        "credentials": {
          "oauthClient": {
            "token_endpoint_auth_method": "client_secret_basic"
          }
        },
        "settings": {
            "oauthClient": {
                "client_uri": "http://localhost:3000",
                "logo_uri": None,
                "redirect_uris": redirect_uris,
                "response_types": ["code"],
                "grant_types": ["authorization_code", "refresh_token"],
                "application_type": "web",
                "consent_method": "TRUSTED"
            }
        }
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_token}' 
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Okta API Error: {e.code} - {error_body}")
        raise Exception(f"Okta API Error: {error_body}")

def handler(event, context):
    logger.info(f"DCR request: {json.dumps(event)}")

    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return response(400, {'error': 'invalid_request', 'error_description': 'Invalid JSON body'})

    # Extract client metadata
    raw_client_name = body.get('client_name', f"dcr-client-{uuid.uuid4().hex[:8]}")
    client_name = re.sub(r'[^\w\s\-().]', '', raw_client_name).strip() or "Client"

    redirect_uris = body.get('redirect_uris', ['http://localhost:3000'])

    # Validate redirect URIs
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return response(400, {'error': 'invalid_redirect_uri', 'error_description': 'redirect_uris must be a non-empty array'})

    okta_domain = os.environ['OKTA_DOMAIN']
    client_id_service = os.environ['OKTA_CLIENT_ID']
    client_secret_service = os.environ['OKTA_CLIENT_SECRET']
    app_group_id = os.environ['OKTA_APP_GROUP_ID']
    gateway_name = os.environ['GATEWAY_NAME']

    try:
        # 1. Get Access Token
        access_token = get_okta_token(okta_domain, client_id_service, client_secret_service)

        # 2. Create Okta Client
        okta_app = create_okta_client(client_name, redirect_uris, access_token, okta_domain)
        
        okta_app_id = okta_app['id'] # The internal Okta ID (e.g., 0oa...)
        new_client_id = okta_app['credentials']['oauthClient']['client_id']
        new_client_secret = okta_app['credentials']['oauthClient']['client_secret']

        logger.info(f"Created Okta client: {new_client_id} (Okta ID: {okta_app_id})")

        # 3. Assign to Group (Critical for Scoped Admin Roles)
        assign_app_to_group(okta_app_id, app_group_id, access_token, okta_domain)

        # 4. Add client to gateway AllowedClients
        gateway_id = find_gateway_by_name(gateway_name)
        if gateway_id:
            try:
                gateway = agentcore.get_gateway(gatewayIdentifier=gateway_id)

                current_clients = gateway.get('authorizerConfiguration', {}).get('customJWTAuthorizer', {}).get('allowedClients', [])
                updated_clients = list(set(current_clients + [new_client_id]))

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
                logger.info(f"Added client {new_client_id} to gateway AllowedClients")
            except Exception as e:
                logger.error(f"Failed to update gateway: {e}")
        else:
            logger.warning(f"Gateway '{gateway_name}' not found - client created but not added to AllowedClients")

        # Return RFC 7591 compliant response
        return response(201, {
            'client_id': new_client_id,
            'client_secret': new_client_secret,
            'client_name': client_name,
            'redirect_uris': redirect_uris,
            'token_endpoint_auth_method': 'client_secret_basic',
            'grant_types': ['authorization_code', 'refresh_token'],
            'response_types': ['code']
        })

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
