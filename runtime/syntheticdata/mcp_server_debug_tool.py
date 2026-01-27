
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
