from mcp.server.fastmcp import FastMCP
print(dir(FastMCP))
try:
    mcp = FastMCP("test")
    print("\nInstance dir:")
    print(dir(mcp))
except Exception as e:
    print(e)
