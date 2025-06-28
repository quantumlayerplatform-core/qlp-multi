"""
Model Context Protocol Integration for Quantum Layer Platform
Enables standardized context sharing and tool use across agents
"""

from .mcp_server import MCPServer, MCPPromptServer, MCPTool, MCPResource
from .mcp_client import MCPClient, MCPContextClient
from .context_manager import ContextManager, MCPContextBridge

# Import context enhancement if available
try:
    from .context_enhancement import (
        enhance_request_with_mcp_context,
        update_mcp_from_result,
        get_context_manager,
        get_context_bridge
    )
    _context_enhancement_available = True
except ImportError:
    _context_enhancement_available = False

__all__ = [
    "MCPServer",
    "MCPPromptServer",
    "MCPClient",
    "MCPContextClient",
    "MCPTool",
    "MCPResource",
    "ContextManager",
    "MCPContextBridge"
]

if _context_enhancement_available:
    __all__.extend([
        "enhance_request_with_mcp_context",
        "update_mcp_from_result",
        "get_context_manager",
        "get_context_bridge"
    ])
