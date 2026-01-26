# Syntheticdata MCP Server Runtime Deployment

This folder contains the configuration and scripts to deploy the AWS Labs syntheticdata-mcp-server 
to Amazon Bedrock AgentCore Runtime.

## Overview

The syntheticdata-mcp-server provides tools for generating synthetic data based on business descriptions. 
Once deployed to AgentCore Runtime, it can be added as a gateway target.

## Tools Provided

| Tool Name | Description |
|-----------|-------------|
| `get_data_gen_instructions` | Get instructions for generating synthetic data based on a business description |
| `execute_pandas_code` | Execute pandas code to generate synthetic data and save it as CSV files |
| `validate_and_save_data` | Validate JSON Lines data structure and save it as CSV files |
| `load_to_storage` | Load data to storage targets like S3 with support for multiple formats |

## Prerequisites

- Python 3.10+
- AWS credentials configured
- Docker daemon running
- Required packages: `bedrock-agentcore-starter-toolkit`, `awslabs.syntheticdata-mcp-server`

## Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Deploy to AgentCore Runtime

```bash
python deploy_runtime.py
```

This will:
1. Configure the AgentCore Runtime with the syntheticdata MCP server
2. Build and push the Docker image to ECR
3. Deploy the runtime and return the Agent ARN

### 3. Test the Deployment

```bash
python test_runtime.py
```

### 4. Add to Gateway (Terraform)

After successful deployment, update your `terraform.tfvars`:

```hcl
syntheticdata_runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-id"
```

Then run:

```bash
cd ../terraform
terraform apply
```

## Files

- `mcp_server.py` - MCP server wrapper for syntheticdata tools
- `requirements.txt` - Python dependencies  
- `deploy_runtime.py` - Deployment script using AgentCore SDK
- `test_runtime.py` - Test script for the deployed runtime

## Reference

- [AWS Labs Syntheticdata MCP Server](https://awslabs.github.io/mcp/servers/syntheticdata-mcp-server)
- [AgentCore Runtime Tutorial](../../amazon-bedrock-agentcore-samples/01-tutorials/01-AgentCore-runtime/02-hosting-MCP-server/)
