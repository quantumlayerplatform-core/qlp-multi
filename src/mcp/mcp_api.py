"""
FastAPI endpoint for MCP integration
Exposes QLP capabilities via Model Context Protocol
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio

from src.mcp import MCPServer, MCPPromptServer, ContextManager, MCPContextBridge
import structlog

logger = structlog.get_logger()

# Create MCP app
mcp_app = FastAPI(
    title="QLP MCP Server",
    description="Model Context Protocol endpoint for Quantum Layer Platform",
    version="1.0.0"
)

# Enable CORS for MCP clients
mcp_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make context manager globally accessible
_global_context_manager = None
_global_context_bridge = None

def get_shared_context_manager():
    """Get the shared context manager instance"""
    global _global_context_manager, _global_context_bridge
    if _global_context_manager is None:
        from src.mcp import ContextManager, MCPContextBridge
        _global_context_manager = ContextManager(max_frames=200)
        _global_context_bridge = MCPContextBridge(_global_context_manager)
    return _global_context_manager, _global_context_bridge

# Initialize MCP components
mcp_server = MCPPromptServer(name="qlp-mcp", version="1.0.0")
context_manager, context_bridge = get_shared_context_manager()


class MCPRequest(BaseModel):
    """MCP protocol request"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP protocol response"""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@mcp_app.post("/mcp", response_model=MCPResponse)
async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle MCP protocol requests"""
    try:
        logger.info(f"MCP request: {request.method}")
        
        # Special handling for context-aware methods
        if request.method == "tools/call" and request.params:
            tool_name = request.params.get("name")
            
            # Inject context for code generation
            if tool_name == "generate_code":
                # Add active context to requirements
                active_context = context_manager.get_active_context()
                if "arguments" in request.params:
                    args = request.params["arguments"]
                    if "requirements" not in args:
                        args["requirements"] = {}
                    args["requirements"]["context"] = active_context
                    
                    # Add context narrative
                    args["requirements"]["context_narrative"] = context_manager.build_narrative_context()
        
        # Process request
        result = await mcp_server.handle_request({
            "method": request.method,
            "params": request.params
        })
        
        # Update context based on results
        if request.method == "tools/call" and "content" in result:
            # Extract and store relevant context
            if request.params.get("name") == "generate_code":
                try:
                    import json
                    content = json.loads(result["content"][0]["text"])
                    context_bridge.update_from_result(content, "mcp_client")
                except:
                    pass
        
        return MCPResponse(
            jsonrpc="2.0",
            result=result,
            id=request.id
        )
        
    except Exception as e:
        logger.error(f"MCP error: {str(e)}")
        return MCPResponse(
            jsonrpc="2.0",
            error={
                "code": -32603,
                "message": str(e)
            },
            id=request.id
        )


@mcp_app.get("/health")
async def health():
    """MCP health check"""
    return {
        "status": "healthy",
        "server": mcp_server.name,
        "version": mcp_server.version,
        "tools": len(mcp_server.tools),
        "resources": len(mcp_server.resources),
        "prompts": len(mcp_server.prompts),
        "context_frames": len(context_manager.frames),
        "active_task": context_manager.active_task_id is not None
    }


@mcp_app.get("/context")
async def get_mcp_context():
    """Get current MCP context state"""
    return {
        "active_context": context_manager.get_active_context(),
        "narrative": context_manager.build_narrative_context(),
        "frame_count": len(context_manager.frames),
        "frame_types": {
            frame_type: len(frames)
            for frame_type, frames in context_manager.type_index.items()
        }
    }


@mcp_app.post("/context/reset")
async def reset_mcp_context():
    """Reset MCP context"""
    global context_manager
    context_manager = ContextManager(max_frames=200)
    return {"status": "context_reset"}


# Integration with main app
def integrate_mcp_with_app(app: FastAPI):
    """Integrate MCP endpoints with main FastAPI app"""
    app.mount("/mcp", mcp_app)
    logger.info("MCP endpoints mounted at /mcp")


# Standalone server for testing
if __name__ == "__main__":
    import uvicorn
    
    @mcp_app.on_event("startup")
    async def startup():
        logger.info("MCP Server starting...")
        logger.info(f"Available tools: {list(mcp_server.tools.keys())}")
        logger.info(f"Available resources: {list(mcp_server.resources.keys())}")
    
    uvicorn.run(mcp_app, host="0.0.0.0", port=8005)
