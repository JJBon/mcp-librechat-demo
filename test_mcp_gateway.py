import asyncio
import os
import sys
import logging
from mcp import ClientSession, StdioServerParameters
# Use the streamable http client from your runtime folder if available, or just use htppx/mcp
sys.path.append(os.path.join(os.getcwd(), 'runtime/syntheticdata'))
try:
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("Could not import streamablehttp_client. Please ensure requirements are installed.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway_test")

GATEWAY_URL = "https://main-gate-gateway-r7puam6qfe.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

async def run_test(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Amzn-Bedrock-AgentCore-Runtime-User-Id": "test-user-123"
    }
    
    print(f"Connecting to Gateway: {GATEWAY_URL}")
    print(f"Using Token: {token[:10]}...")

    try:
        async with streamablehttp_client(GATEWAY_URL, headers=headers, timeout=30) as (read, write, _):
            async with ClientSession(read, write) as session:
                print("Initializing...")
                await session.initialize()
                print("Initialized!")
                
                print("Initialized!")
                
                tool_name = "main-gate-SyntheticData-Target-v8___get_data_gen_instructions"
                print(f"Invoking tool: {tool_name} to trigger 3LO...")
                
                try:
                    result = await session.call_tool(
                        name=tool_name,
                        arguments={"business_description": "testing 3lo flow for e-commerce"}
                    )
                    print("\n--- Tool Result ---")
                    # Check if result contains auth url or text
                    for content in result.content:
                        print(f"Type: {content.type}")
                        if hasattr(content, 'text'):
                            print(f"Text: {content.text}")
                        else:
                            print(f"Content: {content}")
                    print("-------------------\n")
                except Exception as e:
                    print(f"\n❌ Tool Execution Failed: {e}")
                
    except Exception as e:
        print(f"Connection Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_mcp_gateway.py <access_token>")
        # Try to get token from debug_token.py output if not provided
        # But for now, just exit
        sys.exit(1)
    
    token = sys.argv[1]
    asyncio.run(run_test(token))
