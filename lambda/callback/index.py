import json
import logging
import os
import boto3
from urllib.parse import parse_qs

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_boto_client(service_name, region_name=None):
    """Get a boto3 client for the specified service."""
    session = boto3.Session()
    return session.client(service_name, region_name=region_name or os.environ.get('AWS_REGION'))

def lambda_handler(event, context):
    """
    Handle OAuth2 Callback from Provider (e.g. Okta).
    Expected Query Params: code, state (which maps to session_id internally?), or session_id directly?
    
    Ref: oauth2_callback_server.py expects 'session_id' param.
    But typical OAuth2 providers return 'code' and 'state'.
    AgentCore + 3LO might map 'state' to 'session_id' or return it directly.
    """
    logger.info(f"Event: {json.dumps(event)}")
    
    query_params = event.get('queryStringParameters', {}) or {}
    
    # Check for 'session_id' (AgentCore specific?) or 'code'/'state' (Standard OAuth)
    session_id = query_params.get('session_id')
    code = query_params.get('code')
    state = query_params.get('state')
    
    # If standard OAuth, maybe 'state' IS the session_id or contains it?
    # For now, let's log everything.
    
    if not session_id and state:
        logger.info("No session_id found, using state as session_identifier")
        session_id = state
        
    if not session_id:
        return {
            'statusCode': 400,
            'body': 'Missing session_id or state parameter'
        }

    try:
        # We need to complete the handshake.
        # The 'user_identifier' is critical. 
        # In a generic public callback, we don't know the User Identity unless:
        # 1. It's in the state/session_id
        # 2. We have a way to look it up.
        
        # NOTE: For this implementation, we are using a simplified assumption or 
        # trying to find if IdentityClient can handle it.
        # Since we don't have the 'bedrock_agentcore' SDK's IdentityClient 
        # easily available/configured in this context without more setup,
        # we will attempt to use Boto3 directly if possible.
        
        # Searching for the API name... 'CompleteResourceTokenAuth' isn't standard Boto3 yet?
        # It might be in 'bedrock-agent-runtime'.
        # Let's try to initialize the SDK if installed.
        
        try:
            from bedrock_agentcore.services.identity import IdentityClient, UserTokenIdentifier
            
            # IDENTITY BINDING CHALLENGE:
            # We need the user_token to bind the session.
            # For the DEMO, if we are single user, we might mock it or look for it in the query?
            # If AgentCore passed it in the redirect (as suggested by docs), it might be a param.
            
            # Let's assume for now we just log success and instructions.
            # Ideally, we call:
            # client = IdentityClient()
            # client.complete_resource_token_auth(session_uri=session_id, user_identifier=...)
            
            logger.info("Successfully received Callback. Proceeding to auth completion.")
            
            # Placeholder: In a real multi-tenant app, we'd look up the User Identity here.
            # For now, we simply ACK the callback.
            
        except ImportError:
            logger.warning("bedrock_agentcore SDK not found. Skipping SDK call.")

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': """
            <html>
                <body>
                    <h1>OAuth Flow Callback Received</h1>
                    <p>You can close this window. (Note: Session Binding pending User Identity Lookups)</p>
                </body>
            </html>
            """
        }
        
    except Exception as e:
        logger.error(f"Error handling callback: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Internal Error: {str(e)}"
        }
