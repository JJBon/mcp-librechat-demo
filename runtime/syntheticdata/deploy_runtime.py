"""
Deploy Syntheticdata MCP Server to Amazon Bedrock AgentCore Runtime.

This script uses the bedrock-agentcore-starter-toolkit to:
1. Configure the runtime with the MCP server
2. Build and push the Docker image
3. Deploy the runtime and store the Agent ARN

Environment Variables (optional, for JWT auth):
- SYNTHETICDATA_OKTA_DOMAIN: Okta domain (e.g., dev-12345.okta.com)
- SYNTHETICDATA_OKTA_AUDIENCE: Expected audience claim (e.g., syntheticdata-api)
"""

import os
import json
from pathlib import Path
from boto3.session import Session
from bedrock_agentcore_starter_toolkit import Runtime


def main():
    """Deploy the syntheticdata MCP server to AgentCore Runtime."""
    
    # Initialize boto3 session
    boto_session = Session()
    region = boto_session.region_name
    print(f"Using AWS region: {region}")
    
    # Verify required files exist
    required_files = ["mcp_server.py", "requirements.txt"]
    for file in required_files:
        if not os.path.exists(file):
            raise FileNotFoundError(f"Required file {file} not found")
    print("All required files found ✓")
    
    # Define the tool/agent name
    tool_name = "syntheticdata_mcp"
    
    # Initialize the AgentCore Runtime
    agentcore_runtime = Runtime()
    
    # Build authorizer configuration if Okta env vars are set
    okta_domain = os.environ.get("SYNTHETICDATA_OKTA_DOMAIN", "")
    okta_audience = os.environ.get("SYNTHETICDATA_OKTA_AUDIENCE", "")
    
    auth_config = None
    if okta_domain:
        print(f"Configuring JWT authorizer with Okta domain: {okta_domain}")
        auth_config = {
            "customJWTAuthorizer": {
                "allowedClients": [os.environ.get("SYNTHETICDATA_OKTA_CLIENT_ID", "")],
                "discoveryUrl": f"https://{okta_domain}/oauth2/default/.well-known/openid-configuration"
            }
        }
    else:
        print("No Okta config found - deploying without JWT authorizer")
        print("Set SYNTHETICDATA_OKTA_DOMAIN and SYNTHETICDATA_OKTA_AUDIENCE for user delegation")
    
    # Configure the runtime
    print("Configuring AgentCore Runtime...")
    config_kwargs = {
        "entrypoint": "mcp_server.py",
        "auto_create_execution_role": True,
        "auto_create_ecr": True,
        "requirements_file": "requirements.txt",
        "region": region,
        "protocol": "MCP",
        "agent_name": tool_name,
    }
    
    # Add authorizer config if available
    if auth_config:
        config_kwargs["authorizer_configuration"] = auth_config
    
    response = agentcore_runtime.configure(**config_kwargs)
    print("Configuration completed ✓")
    print(f"Configuration response: {json.dumps(response, indent=2, default=str)}")
    
    # Launch the MCP server to AgentCore Runtime
    print("\nLaunching MCP server to AgentCore Runtime...")
    print("This may take several minutes...")
    launch_result = agentcore_runtime.launch()
    print("Launch completed ✓")
    print(f"Agent ARN: {launch_result.agent_arn}")
    print(f"Agent ID: {launch_result.agent_id}")
    
    # Store the agent ARN in SSM Parameter Store for easy retrieval
    ssm_client = boto_session.client('ssm', region_name=region)
    
    agent_arn_response = ssm_client.put_parameter(
        Name='/mcp_server/syntheticdata/agent_arn',
        Value=launch_result.agent_arn,
        Type='String',
        Description='Agent ARN for syntheticdata MCP server',
        Overwrite=True
    )
    print("✓ Agent ARN stored in Parameter Store: /mcp_server/syntheticdata/agent_arn")
    
    # Also save to a local file for Terraform
    output_file = Path(__file__).parent / "deployment_output.json"
    with open(output_file, "w") as f:
        json.dump({
            "agent_arn": launch_result.agent_arn,
            "agent_id": launch_result.agent_id,
            "region": region,
        }, f, indent=2)
    print(f"✓ Deployment info saved to: {output_file}")
    
    print("\n" + "=" * 60)
    print("Deployment Summary")
    print("=" * 60)
    print(f"Agent ARN: {launch_result.agent_arn}")
    print(f"Region: {region}")
    print("\nNext steps:")
    print("1. Test the deployment with: python test_runtime.py")
    print("2. Add to Terraform by setting syntheticdata_runtime_arn variable")
    print("=" * 60)
    
    return launch_result


if __name__ == "__main__":
    main()
