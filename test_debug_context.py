import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client

# Configuration
GATEWAY_URL = "https://main-gate-gateway-r7puam6qfe.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
# This token mimics a valid-looking JWT structure but is for M2M auth testing
MOCK_TOKEN = "eyJraWQiOiJHOGhwWEhoZ2ZMeDBya2NiZzJITWtaU0F2UWNrdXF0U0Y3YWMxVFc4dWNNIiwiYWxnIjoiUlMyNTYifQ.eyJ2ZXIiOjEsImp0aSI6IkFULjlSby0wclBGRjVsa19LUEJmcDJUQVpkVDNoazhPTGE0Zzg3Zk9paVJtZVUiLCJpc3MiOiJodHRwczovL3R3aWxpby1ob21ld29yay5va3RhcHJldmlldy5jb20vb2F1dGgyL2RlZmF1bHQiLCJhdWQiOiJhcGk6Ly9kZWZhdWx0IiwiaWF0IjoxNzY5NTMxODU3LCJleHAiOjE3Njk1MzU0NTcsImNpZCI6IjBvYXU4c2gzazdCOG5LWGdkMWQ3Iiwic2NwIjpbInN5bnRoZXRpY2RhdGE6aW52b2tlIl0sInN1YiI6IjBvYXU4c2gzazdCOG5LWGdkMWQ3IiwiYWdlbnRjb3JlLWNsYWltIjoiMG9hdThzaDNrN0I4bktYZ2QxZDciLCJjbGllbnRfaWQiOiIwb2F1OHNoM2s3QjhuS1hnZDFkNyJ9.KKf6y9S9MtLbKftPKZyBm_PbP8TwokIOELfESBF0sQ_0UciLXFBLpWobYeAgQ-ANPkDAVMLAwyFszIBvrm7EfY1ZdnXwfCpByzKUyjWd6xZkMQ9n-HOHYRrx3MuACEAcw1I4u35rAxbFxfyL5ZahqYw2BsGLeaZYN0NLMNF0KBQTB6mOBZvIhMLTfdCjXBmodEGrgA9XnB1O5kG4jxQ16EfwYLf_TAaIO6gZ0Pe4ZKTJ2_XBVN2X8heMh2qZNHwv1xYchHr5oyINsWpOvS6qgvFfWPGYq5chqx33p4reedGSCZz8EkhVzAKoLPlZOHh1-whMvp9gcNZ5_6CU859-fg"

if len(sys.argv) > 1:
    MOCK_TOKEN = sys.argv[1]

# Header to trigger 3LO flow (which we want to inspect context for)
HEADERS = {
    "Authorization": f"Bearer {MOCK_TOKEN}",
    "X-Amzn-Bedrock-AgentCore-Runtime-User-Id": "test-user-123-debug" 
}

async def run():
    print(f"Connecting to Gateway: {GATEWAY_URL}")
    
    async with streamablehttp_client(GATEWAY_URL, headers=HEADERS, timeout=30.0) as (read, write, _):
        print("Initializing...")
        
        async with ClientSession(read, write) as session:
            print("Initializing session...")
            await session.initialize()
            print("Initialized!")
            
            print("Listing tools...")
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            target_tool = "main-gate-SyntheticData-Target-v8___debug_context"
            if target_tool not in [t.name for t in tools.tools]:
                 print(f"WARNING: Target tool {target_tool} not found in list!")
            
            print(f"Invoking tool: {target_tool}...")
            
            try:
                result = await session.call_tool(
                    "main-gate-SyntheticData-Target-v8___debug_context",
                    arguments={}
                )
                print("\n--- Tool Result ---")
                # Handle content
                if hasattr(result, 'content'):
                    for content in result.content:
                        if content.type == 'text':
                            print(f"Text: {content.text}")
                        else:
                            print(f"Content: {content}")
                else:
                    print(result)
                print("-------------------")
                
            except Exception as e:
                print(f"Error executing tool: {e}")

if __name__ == "__main__":
    asyncio.run(run())
