import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
async def test():
    async with streamablehttp_client('http://localhost:8000/mcp', {}, timeout=30, terminate_on_close=False) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('Available tools:')
            for tool in tools.tools:
                print(f'  - {tool.name}: {tool.description[:60]}...')
asyncio.run(test())