"""
MCP Client for connecting to QLP MCP Server
Enables external tools and LLMs to use QLP capabilities
"""

import httpx
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class MCPClient:
    """
    Client for interacting with QLP via Model Context Protocol
    Can be used by external LLMs, tools, or applications
    """
    
    def __init__(self, server_url: str = "http://localhost:8005/mcp"):
        self.server_url = server_url
        self.session_id = f"mcp-client-{datetime.utcnow().timestamp()}"
        self.client = httpx.AsyncClient(timeout=300.0)
        self.initialized = False
        self.server_capabilities = {}
        self.available_tools = {}
        self.available_resources = {}
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize connection with MCP server"""
        response = await self._request("initialize", {
            "sessionId": self.session_id,
            "clientInfo": {
                "name": "qlp-mcp-client",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": True,
                "resources": True
            }
        })
        
        if "serverInfo" in response:
            self.server_capabilities = response["serverInfo"]["capabilities"]
            self.initialized = True
            
            # Fetch available tools and resources
            await self._fetch_tools()
            await self._fetch_resources()
            
        return response
    
    async def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the MCP server"""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": f"{self.session_id}-{datetime.utcnow().timestamp()}"
        }
        
        response = await self.client.post(self.server_url, json=request_data)
        response.raise_for_status()
        
        result = response.json()
        if "error" in result:
            raise Exception(f"MCP Error: {result['error']}")
        
        return result.get("result", {})
    
    async def _fetch_tools(self):
        """Fetch available tools from server"""
        if self.server_capabilities.get("tools"):
            response = await self._request("tools/list")
            for tool in response.get("tools", []):
                self.available_tools[tool["name"]] = tool
    
    async def _fetch_resources(self):
        """Fetch available resources from server"""
        if self.server_capabilities.get("resources"):
            response = await self._request("resources/list")
            for resource in response.get("resources", []):
                self.available_resources[resource["uri"]] = resource
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server"""
        if not self.initialized:
            await self.initialize()
        
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        response = await self._request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        # Extract content from response
        if "content" in response and len(response["content"]) > 0:
            content = response["content"][0]
            if content["type"] == "text":
                try:
                    return json.loads(content["text"])
                except json.JSONDecodeError:
                    return content["text"]
        
        return response
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server"""
        if not self.initialized:
            await self.initialize()
        
        response = await self._request("resources/read", {"uri": uri})
        
        if "contents" in response and len(response["contents"]) > 0:
            content = response["contents"][0]
            if content["mimeType"] == "application/json":
                return json.loads(content["text"])
            else:
                return content["text"]
        
        return response
    
    async def update_resource(self, uri: str, content: Any) -> bool:
        """Update a mutable resource on the MCP server"""
        if not self.initialized:
            await self.initialize()
        
        if isinstance(content, dict):
            content_str = json.dumps(content)
        else:
            content_str = str(content)
        
        response = await self._request("resources/update", {
            "uri": uri,
            "content": content_str
        })
        
        return response.get("success", False)
    
    async def generate_code(
        self,
        description: str,
        requirements: Optional[Dict[str, Any]] = None,
        strategy: str = "production"
    ) -> Dict[str, Any]:
        """Generate code using QLP's ensemble agents"""
        return await self.call_tool("generate_code", {
            "description": description,
            "requirements": requirements or {},
            "agent_strategy": strategy
        })
    
    async def search_patterns(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar patterns in memory"""
        return await self.call_tool("search_memory", {
            "query": query,
            "type": "pattern",
            "limit": limit
        })
    
    async def get_principles(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """Get software engineering principles"""
        principles = await self.read_resource("qlp://principles/software-engineering")
        
        if category and category in principles:
            return {category: principles[category]}
        
        return principles
    
    async def get_active_genomes(self) -> Dict[str, Any]:
        """Get currently active prompt genomes"""
        return await self.read_resource("qlp://genomes/active")
    
    async def evolve_genomes(self, role: str, strategy: str = "explanation_depth") -> Dict[str, Any]:
        """Trigger genome evolution for a specific role"""
        return await self.call_tool("evolve_genome", {
            "role": role,
            "strategy": strategy
        })
    
    async def close(self):
        """Close the client connection"""
        await self.client.aclose()


class MCPContextClient(MCPClient):
    """
    Extended MCP client with context management capabilities
    Maintains conversation context across multiple interactions
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_stack: List[Dict[str, Any]] = []
        self.active_context: Dict[str, Any] = {}
    
    def push_context(self, context: Dict[str, Any]):
        """Push new context onto the stack"""
        self.context_stack.append(self.active_context.copy())
        self.active_context.update(context)
        logger.info(f"Pushed context: {list(context.keys())}")
    
    def pop_context(self) -> Dict[str, Any]:
        """Pop context from the stack"""
        if self.context_stack:
            previous = self.active_context
            self.active_context = self.context_stack.pop()
            return previous
        return {}
    
    def add_to_context(self, key: str, value: Any):
        """Add a value to the active context"""
        self.active_context[key] = value
    
    def get_from_context(self, key: str, default: Any = None) -> Any:
        """Get a value from the active context"""
        return self.active_context.get(key, default)
    
    async def generate_with_context(
        self,
        description: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate code with accumulated context"""
        
        # Merge contexts
        full_context = self.active_context.copy()
        if additional_context:
            full_context.update(additional_context)
        
        # Add context to requirements
        requirements = full_context.get("requirements", {})
        requirements["context"] = full_context
        
        result = await self.generate_code(
            description=description,
            requirements=requirements
        )
        
        # Store result in context for future reference
        self.add_to_context("last_result", result)
        
        return result
    
    async def refine_with_feedback(
        self,
        feedback: str,
        previous_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Refine previous generation based on feedback"""
        
        if previous_result is None:
            previous_result = self.get_from_context("last_result", {})
        
        refinement_description = f"""
        Refine the previous code based on this feedback: {feedback}
        
        Previous code:
        {previous_result.get('code', 'No previous code')}
        
        Apply the feedback and improve the solution.
        """
        
        # Add feedback to context
        self.push_context({
            "feedback": feedback,
            "previous_code": previous_result.get('code', '')
        })
        
        result = await self.generate_with_context(refinement_description)
        
        self.pop_context()
        
        return result


# Example usage function
async def example_mcp_usage():
    """Example of using MCP client with QLP"""
    
    client = MCPContextClient()
    
    try:
        # Initialize connection
        await client.initialize()
        print("✅ Connected to QLP MCP Server")
        
        # Set project context
        client.add_to_context("project", "e-commerce-platform")
        client.add_to_context("tech_stack", {
            "backend": "FastAPI",
            "database": "PostgreSQL",
            "cache": "Redis"
        })
        
        # Generate initial code
        result = await client.generate_with_context(
            "Create a product catalog service with search functionality"
        )
        
        print(f"📊 Generated with {result.get('confidence', 0):.1%} confidence")
        
        # Get principles used
        principles = await client.get_principles("architecture")
        print(f"🏛️ Using {len(principles.get('architecture', []))} architecture principles")
        
        # Search for similar patterns
        patterns = await client.search_patterns("catalog search", limit=3)
        print(f"🔍 Found {len(patterns)} similar patterns")
        
        # Refine based on feedback
        refined = await client.refine_with_feedback(
            "Add pagination and filtering by category"
        )
        
        print(f"✨ Refined with {refined.get('confidence', 0):.1%} confidence")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_mcp_usage())
