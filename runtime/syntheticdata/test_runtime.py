"""
Test the deployed Syntheticdata MCP Server on AgentCore Runtime.

This script connects to the deployed MCP server and tests the available tools.
"""

import asyncio
import sys
import json
import logging
import boto3
from boto3.session import Session
from mcp import ClientSession
from streamable_http_sigv4 import streamablehttp_client_with_sigv4

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_streamable_http_transport_sigv4(mcp_url: str, service_name: str, region: str):
    """
    Create a streamable HTTP transport with AWS SigV4 authentication.
    """
    session = boto3.Session()
    credentials = session.get_credentials()

    return streamablehttp_client_with_sigv4(
        url=mcp_url,
        credentials=credentials,
        service=service_name,
        region=region,
    )


async def main():
    """Test the deployed syntheticdata MCP server."""
    
    boto_session = Session()
    region = boto_session.region_name
    print(f"Using AWS region: {region}")

    ssm_client = boto3.client("ssm", region_name=region)

    # Try to get the agent ARN from SSM Parameter Store
    try:
        agent_arn_response = ssm_client.get_parameter(
            Name="/mcp_server/syntheticdata/agent_arn"
        )
        agent_arn = agent_arn_response["Parameter"]["Value"]
        print(f"Retrieved Agent ARN: {agent_arn}")
    except ssm_client.exceptions.ParameterNotFound:
        print("❌ Error: Agent ARN not found in SSM Parameter Store")
        print("Please run deploy_runtime.py first")
        sys.exit(1)

    if not agent_arn:
        print("❌ Error: AGENT_ARN is empty")
        sys.exit(1)

    # Build the MCP URL
    encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

    try:
        async with create_streamable_http_transport_sigv4(
            mcp_url=mcp_url, service_name="bedrock-agentcore", region=region
        ) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                print("\n🔄 Initializing MCP session...")
                await session.initialize()
                print("✓ MCP session initialized")

                print("\n🔄 Listing available tools...")
                tool_result = await session.list_tools()

                print("\n📋 Available MCP Tools:")
                print("=" * 60)
                for tool in tool_result.tools:
                    print(f"🔧 {tool.name}")
                    print(f"   Description: {tool.description}")
                    if hasattr(tool, "inputSchema") and tool.inputSchema:
                        properties = tool.inputSchema.get("properties", {})
                        if properties:
                            print(f"   Parameters: {list(properties.keys())}")
                    print()

                print(f"✅ Successfully connected to MCP server!")
                print(f"Found {len(tool_result.tools)} tools available.")

                # Test the get_data_gen_instructions tool
                print("\n🧪 Testing Tools:")
                print("=" * 60)

                try:
                    print("\n📝 Testing get_data_gen_instructions...")
                    result = await session.call_tool(
                        name="get_data_gen_instructions",
                        arguments={
                            "business_description": "An e-commerce platform with customers, products, and orders"
                        },
                    )
                    print(f"   Result preview: {str(result.content[0].text)[:200]}...")
                    print("   ✓ Tool executed successfully")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

                print("\n✅ MCP tool testing completed!")

    except Exception as e:
        print(f"❌ Error connecting to MCP server: {e}")
        import traceback

        print("\n🔍 Full error traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
