"""
Syntheticdata MCP Server for Amazon Bedrock AgentCore Runtime.

This wraps the awslabs.syntheticdata-mcp-server as a FastMCP server
compatible with AgentCore Runtime hosting requirements.
"""

from mcp.server.fastmcp import FastMCP
from awslabs.syntheticdata_mcp_server.server import (
    get_data_gen_instructions,
    validate_and_save_data,
    load_to_storage,
    execute_pandas_code,
    ValidateAndSaveDataInput,
    LoadToStorageInput,
    ExecutePandasCodeInput,
)
from pydantic import Field
from typing import Dict, List, Any

# Create FastMCP server with stateless_http=True for AgentCore Runtime compatibility
print("--- SYNTHETICDATA MCP SERVER STARTING (3LO ENABLED v3) ---")

mcp = FastMCP(
    name="syntheticdata-mcp-server",
    host="0.0.0.0",
    stateless_http=True,
    instructions="""
    # Syntheticdata MCP Server
    
    This MCP server provides tools for generating high-quality synthetic data based on business use cases.
    
    ## Capabilities
    
    - Provides detailed instructions for generating synthetic data based on business descriptions
    - Executes pandas code safely to generate data
    - Validates and saves JSON Lines data as CSV files
    - Loads data to various storage targets (S3, with more coming soon)
    - Supports multiple data formats (CSV, JSON, Parquet)
    - Handles data partitioning and storage optimization
    
    ## Workflow
    
    1. Start by describing your business domain and use case
    2. Get detailed instructions for generating synthetic data
    3. Generate the data using pandas code or JSON Lines format
    4. Validate and save the data as CSV files
    5. (Optional) Load the data to storage targets like S3
    """
)


from mcp.server.fastmcp import Context

# Duplicate tool definition removed to ensure 3LO version is used

# 3LO Configuration
CALLBACK_URL = "https://cr5ori8f7e.execute-api.us-east-1.amazonaws.com/prod/callback"
PROVIDER_NAME = "main-gate-okta-3lo-provider" # Must match Terraform
SCOPES = ["syntheticdata:invoke"]

from bedrock_agentcore.identity.auth import requires_access_token

# Internal logic with auth decorator
@requires_access_token(
    provider_name=PROVIDER_NAME,
    scopes=SCOPES,
    auth_flow='USER_FEDERATION',
    force_authentication=True,
    callback_url=CALLBACK_URL
)
async def _internal_get_data_gen_instructions(
    business_description: str,
    ctx: Context = None,
    access_token: str = None,
) -> Dict:
    if ctx and ctx.request_context:
        print(f"DEBUG: Context Meta (Inside Decorator): {ctx.request_context.meta}")
        
    if access_token:
         print(f"FOUND 3LO ACCESS TOKEN: {access_token[:10]}...")

    return await get_data_gen_instructions(business_description=business_description)

@mcp.tool(name="get_data_gen_instructions")
async def tool_get_data_gen_instructions(
    business_description: str = Field(
        ...,
        description="A detailed description of the business domain and use case. The more specific and comprehensive the description, the better the data generation instructions will be.",
    ),
    ctx: Context = None,
    access_token: str = Field(None, description="Injected access token. Do not provide manually."),
) -> Dict:
    """Get instructions for generating synthetic data based on a business description.

    This tool analyzes a business description and provides detailed instructions
    for generating synthetic data in JSON Lines format.

    Parameters:
        business_description: A description of the business use case
        ctx: Request context containing headers (injected)
        access_token: OAuth access token (injected)

    Returns:
        A dictionary containing detailed instructions for generating synthetic data
    """
    # Context Patching for AgentCore Runtime
    if ctx and ctx.request_context:
        print("DEBUG: Wrapper - Patching Context")
        try:
            # If meta is missing but headers exist (FastMCP default behavior)
            print(f"DEBUG: Request Context Type: {type(ctx.request_context)}")
            print(f"DEBUG: Request Context Dir: {dir(ctx.request_context)}")
            
            headers_source = None
            if hasattr(ctx.request_context, 'request') and ctx.request_context.request:
                print(f"DEBUG: Found 'request' in request_context. Type: {type(ctx.request_context.request)}")
                if hasattr(ctx.request_context.request, 'headers'):
                     headers_source = ctx.request_context.request.headers
            elif hasattr(ctx.request_context, 'headers'):
                headers_source = ctx.request_context.headers
            
            if not ctx.request_context.meta and headers_source:
                headers = dict(headers_source)
                print(f"DEBUG: Found headers source: {list(headers.keys())}")
                # Populate meta so the decorator can find 'headers'
                ctx.request_context.meta = {"headers": headers}
                print("DEBUG: Patched ctx.request_context.meta with headers")
            else:
                print(f"DEBUG: Meta exists: {ctx.request_context.meta} OR headers missing in known locations")
        except Exception as e:
            print(f"ERROR patching context: {e}")

    # Delegate to the decorated internal function
    return await _internal_get_data_gen_instructions(
        business_description=business_description,
        ctx=ctx,
        access_token=access_token
    )


@mcp.tool(name="execute_pandas_code")
async def tool_execute_pandas_code(
    code: str = Field(
        ...,
        description='Python code that uses pandas to generate synthetic data. The code should define one or more pandas DataFrames. Pandas is already available as "pd".',
    ),
    workspace_dir: str = Field(
        ...,
        description="CRITICAL: The current workspace directory. Must always be provided to save files to the user's current project.",
    ),
    output_dir: str = Field(
        None,
        description="Optional subdirectory within workspace_dir to save CSV files to. If not provided, files will be saved directly to workspace_dir.",
    ),
) -> Dict:
    """Execute pandas code to generate synthetic data and save it as CSV files.

    This tool runs pandas code in a restricted environment to generate synthetic data.
    It then saves any generated DataFrames as CSV files.

    Parameters:
        code: Python code using pandas to generate synthetic data
        workspace_dir: The current workspace directory
        output_dir: Optional subdirectory for output files

    Returns:
        A dictionary containing execution results and paths to saved CSV files
    """
    input_data = ExecutePandasCodeInput(
        code=code,
        workspace_dir=workspace_dir,
        output_dir=output_dir,
    )
    return await execute_pandas_code(input_data)


@mcp.tool(name="validate_and_save_data")
async def tool_validate_and_save_data(
    data: Dict[str, List[Dict]] = Field(
        ...,
        description="Dictionary mapping table names to lists of records. Each record should be a dictionary mapping column names to values.",
    ),
    workspace_dir: str = Field(
        ...,
        description="CRITICAL: The current workspace directory. Must always be provided to save files to the user's current project.",
    ),
    output_dir: str = Field(
        None,
        description="Optional subdirectory within workspace_dir to save CSV files to. If not provided, files will be saved directly to workspace_dir.",
    ),
) -> Dict:
    """Validate JSON Lines data and save it as CSV files.

    This tool validates the structure of JSON Lines data and saves it as CSV files
    using pandas.

    Parameters:
        data: Dictionary mapping table names to lists of records
        workspace_dir: The current workspace directory
        output_dir: Optional subdirectory for output files

    Returns:
        A dictionary containing validation results and paths to saved CSV files
    """
    input_data = ValidateAndSaveDataInput(
        data=data,
        workspace_dir=workspace_dir,
        output_dir=output_dir,
    )
    return await validate_and_save_data(input_data)


@mcp.tool(name="load_to_storage")
async def tool_load_to_storage(
    data: Dict[str, List[Dict]] = Field(
        ...,
        description="Dictionary mapping table names to lists of records. Each record should be a dictionary mapping column names to values.",
    ),
    targets: List[Dict[str, Any]] = Field(
        ...,
        description='List of target configurations. Each target should have a "type" (e.g., "s3") and target-specific "config".',
    ),
) -> Dict:
    """Load data to one or more storage targets.

    This tool uses the UnifiedDataLoader to load data to configured storage targets.
    Currently supports:
    - S3: Load data as CSV, JSON, or Parquet files with optional partitioning

    Example targets configuration:
    ```python
    targets = [
        {
            'type': 's3',
            'config': {
                'bucket': 'my-bucket',
                'prefix': 'data/users/',
                'format': 'parquet',
                'partitioning': {'enabled': True, 'columns': ['region']},
                'storage': {'class': 'INTELLIGENT_TIERING', 'encryption': 'AES256'},
            },
        }
    ]
    ```

    Parameters:
        data: Dictionary mapping table names to lists of records
        targets: List of target configurations

    Returns:
        Dictionary containing results for each target
    """
    input_data = LoadToStorageInput(
        data=data,
        targets=targets,
    )
    return await load_to_storage(input_data)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

@mcp.tool(name="debug_context")
async def tool_debug_context(ctx: Context = None) -> Dict:
    """Debug tool to inspect the runtime context and headers.
    
    Returns:
        Dictionary containing available context information.
    """
    debug_info = {
        "ctx_exists": ctx is not None,
        "request_context_exists": False,
        "meta_exists": False,
        "headers_in_meta": False,
        "headers_direct": False,
        "all_headers": {},
        "dir_ctx": [],
        "dir_request_context": []
    }
    
    if ctx:
        debug_info["dir_ctx"] = dir(ctx)
        if hasattr(ctx, 'request_context') and ctx.request_context:
            debug_info["request_context_exists"] = True
            debug_info["dir_request_context"] = dir(ctx.request_context)
            
            # Check meta
            if hasattr(ctx.request_context, 'meta'):
                debug_info["meta_exists"] = True
                if ctx.request_context.meta:
                     debug_info["meta_content"] = str(ctx.request_context.meta)
                     if isinstance(ctx.request_context.meta, dict):
                        debug_info["headers_in_meta"] = "headers" in ctx.request_context.meta
            
            # Check headers directly (Starlette/FastAPI style)
            if hasattr(ctx.request_context, 'headers'):
                debug_info["headers_direct"] = True
                # Convert headers to dict for serialization
                debug_info["all_headers"] = dict(ctx.request_context.headers)

    return debug_info
