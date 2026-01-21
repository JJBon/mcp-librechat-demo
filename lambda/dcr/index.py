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
        'scope': 'okta.clients.manage okta.groups.appAssignment.manage okta.clients.read'
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            token_data = json.loads(response.read().decode('utf-8'))
            return token_data.get('access_token')
    except Exception as e:
        logger.error(f"Failed to get Okta access token: {e}")
        raise Exception("Authentication with Okta failed")

def find_existing_client(client_name, api_token, okta_domain):
    """Search for an existing client by name to ensure idempotency"""
    # Note: okta.clients.read scope required
    safe_name = urllib.parse.quote(client_name)
    url = f"https://{okta_domain}/oauth2/v1/clients?q={safe_name}&limit=1"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_token}'
    }

    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req) as response:
            clients = json.loads(response.read().decode('utf-8'))
            # Filter exact match because 'q' is a startsWith search
            for client in clients:
                if client.get('client_name') == client_name:
                    return client
            return None
    except Exception as e:
        logger.warning(f"Failed to search for existing client: {e}")
        return None

def rotate_client_secret(client_id, api_token, okta_domain):
    """Rotates the client secret for an existing client"""
    url = f"https://{okta_domain}/oauth2/v1/clients/{client_id}/lifecycle/newSecret"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_token}'
    }

    try:
        req = urllib.request.Request(url, data=json.dumps({}).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to rotate client secret: {e}")
        raise

def assign_app_to_group(app_id, group_id, api_token, okta_domain):
    """Assigns the newly created Okta App to the AgentCore Group (for scoped administration)"""
    url = f"https://{okta_domain}/api/v1/apps/{app_id}/groups/{group_id}"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_token}'
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps({}).encode('utf-8'), headers=headers, method='PUT')
        with urllib.request.urlopen(req) as response:
            logger.info(f"Assigned app {app_id} to group {group_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to assign app {app_id} to group {group_id}: {e}")
        return False

def create_okta_client(client_name, redirect_uris, api_token, okta_domain):
    """Creates an OIDC App in Okta using the Dynamic Client Registration API"""
    url = f"https://{okta_domain}/oauth2/v1/clients"
    
    payload = {
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "response_types": ["code"],
        "grant_types": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": "client_secret_basic",
        "application_type": "web"
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

def validate_redirect_uris(uris):
    """Validates Redirect URIs based on configuration restrictions"""
    allow_localhost = os.environ.get('ALLOW_LOCALHOST', 'false').lower() == 'true'
    pattern_str = os.environ.get('ALLOWED_DOMAIN_PATTERN', '')
    
    domain_pattern = None
    if pattern_str:
        try:
            domain_pattern = re.compile(pattern_str)
        except re.error as e:
            logger.error(f"Invalid domain regex: {e}")
            # Fail closed? Or open? Let's log and allow if regex is broken to avoid outages, but warn heavily.
            # Ideally fail closed for security.
            return False, "Configuration error: Invalid domain pattern"

    for uri in uris:
        # Check Localhost
        if not allow_localhost:
            if 'localhost' in uri or '127.0.0.1' in uri:
                return False, f"Localhost redirect URIs are not allowed: {uri}"
        
        # Check Allowed Domain Pattern
        if domain_pattern:
            if not domain_pattern.search(uri):
                return False, f"Redirect URI does not match allowed domain pattern: {uri}"
                
    return True, ""

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

    # Validate Format
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return response(400, {'error': 'invalid_redirect_uri', 'error_description': 'redirect_uris must be a non-empty array'})

    # ---------------------------------------------------------
    # RESTRICTION LOGIC: Validate URIs against Policy
    # ---------------------------------------------------------
    valid, msg = validate_redirect_uris(redirect_uris)
    if not valid:
        logger.warning(f"Blocked registration request due to policy: {msg}")
        return response(403, {'error': 'access_denied', 'error_description': msg})
    # ---------------------------------------------------------

    okta_domain = os.environ['OKTA_DOMAIN']
    client_id_service = os.environ['OKTA_CLIENT_ID']
    client_secret_service = os.environ['OKTA_CLIENT_SECRET']
    app_group_id = os.environ['OKTA_APP_GROUP_ID']
    gateway_name = os.environ['GATEWAY_NAME']

    try:
        # 1. Get Access Token
        access_token = get_okta_token(okta_domain, client_id_service, client_secret_service)

        # 2. Check for Existing Client (Idempotency)
        existing_client = find_existing_client(client_name, access_token, okta_domain)
        
        if existing_client:
            logger.info(f"Client '{client_name}' already exists. Rotating secret.")
            new_client_id = existing_client['client_id']
            # Rotate secret to ensure caller has valid credentials
            secret_response = rotate_client_secret(new_client_id, access_token, okta_domain)
            new_client_secret = secret_response['client_secret']
        else:
            # Create New Client
            logger.info(f"Creating new client '{client_name}'")
            okta_app = create_okta_client(client_name, redirect_uris, access_token, okta_domain)
            new_client_id = okta_app['client_id']
            new_client_secret = okta_app['client_secret']

        # 3. Assign to Group (Always do this to ensure even existing apps are correctly grouped)
        assign_app_to_group(new_client_id, app_group_id, access_token, okta_domain)

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
        return response(201 if not existing_client else 200, {
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
