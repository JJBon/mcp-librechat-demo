import json
from typing import Any, Dict


def lambda_handler(event, context):
    """
    Generic Lambda handler for Bedrock AgentCore Gateway placeholder tool.

    Expected input:
        event: {
            # optional tool arguments
            "param_0": val0,
            "param_1": val1,
            ...
        }

    Context should contain:
        context.client_context.custom["bedrockAgentCoreToolName"]
        → e.g. "LambdaTarget___placeholder_tool"
    """
    try:
        extended_name = context.client_context.custom.get("bedrockAgentCoreToolName")
        tool_name = None

        # handle agentcore gateway tool naming convention
        # https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html
        if extended_name and "___" in extended_name:
            tool_name = extended_name.split("___", 1)[1]

        if not tool_name:
            return _response(400, {"error": "Missing tool name"})

        print(f"DEBUG: Executing tool '{tool_name}' with event: {json.dumps(event)}")

        if tool_name == "add_numbers":
            result = add_numbers(event)
            return _response(200, {"result": result})
        elif tool_name == "multiply_numbers":
            result = multiply_numbers(event)
            return _response(200, {"result": result})
        elif tool_name == "greet_user":
            result = greet_user(event)
            return _response(200, {"result": result})
        else:
            return _response(400, {"error": f"Unknown tool '{tool_name}'"})

    except Exception as e:
        return _response(500, {"system_error": str(e)})


def _response(status_code: int, body: Dict[str, Any]):
    """Consistent JSON response wrapper."""
    return {"statusCode": status_code, "body": json.dumps(body)}


def add_numbers(event: Dict[str, Any]) -> int:
    """Add two numbers together"""
    return event.get("a", 0) + event.get("b", 0)


def multiply_numbers(event: Dict[str, Any]) -> int:
    """Multiply two numbers together"""
    return event.get("a", 0) * event.get("b", 0)


def greet_user(event: Dict[str, Any]) -> str:
    """Greet a user by name"""
    name = event.get("name", "Stranger")
    return f"Hello, {name}! Nice to meet you."