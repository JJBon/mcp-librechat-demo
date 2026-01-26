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

@mcp.tool(name="get_data_gen_instructions")
async def tool_get_data_gen_instructions(
    business_description: str = Field(
        ...,
        description="A detailed description of the business domain and use case. The more specific and comprehensive the description, the better the data generation instructions will be.",
    ),
    ctx: Context = None,
) -> Dict:
    """Get instructions for generating synthetic data based on a business description.

    This tool analyzes a business description and provides detailed instructions
    for generating synthetic data in JSON Lines format.

    Parameters:
        business_description: A description of the business use case
        ctx: Request context containing headers (injected)

    Returns:
        A dictionary containing detailed instructions for generating synthetic data
    """
    if ctx and ctx.request_context:
        print(f"DEBUG: Context Meta: {ctx.request_context.meta}")
        headers = ctx.request_context.meta.get("headers", {})
        user_token = headers.get("x-bedrock-user-authorization") or headers.get("X-Bedrock-User-Authorization")
        if user_token:
            print(f"FOUND USER IDENTITY TOKEN: {user_token[:10]}...")
        else:
            print("USER IDENTITY TOKEN NOT FOUND in headers")

    return await get_data_gen_instructions(business_description=business_description)


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
