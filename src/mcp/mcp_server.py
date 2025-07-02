"""
MCP Server Implementation for Quantum Layer Platform
Provides tools and resources to AI agents via Model Context Protocol
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class MCPTool:
    """Represents a tool available via MCP"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    examples: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    """Represents a resource (context) available via MCP"""
    uri: str
    name: str
    description: str
    mime_type: str
    content: Union[str, bytes, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPServer:
    """
    MCP Server that provides tools and resources to AI agents
    Implements the Model Context Protocol specification
    """
    
    def __init__(self, name: str = "qlp-mcp-server", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._initialize_core_tools()
        self._initialize_core_resources()
    
    def _initialize_core_tools(self):
        """Initialize core QLP tools available via MCP"""
        
        # Code generation tool
        self.register_tool(MCPTool(
            name="generate_code",
            description="Generate production-ready code using ensemble agents",
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of what to build"
                    },
                    "requirements": {
                        "type": "object",
                        "description": "Technical requirements and constraints"
                    },
                    "agent_strategy": {
                        "type": "string",
                        "enum": ["ensemble", "production", "meta"],
                        "description": "Agent strategy to use"
                    }
                },
                "required": ["description"]
            },
            handler=self._handle_generate_code,
            examples=[{
                "description": "Create a REST API for user management",
                "requirements": {"framework": "FastAPI", "database": "PostgreSQL"}
            }]
        ))
        
        # Genome evolution tool
        self.register_tool(MCPTool(
            name="evolve_genome",
            description="Evolve prompt genomes based on performance",
            parameters={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "Agent role to evolve"
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["explanation_depth", "conjecture_refutation", "error_correction"],
                        "description": "Evolution strategy"
                    }
                },
                "required": ["role"]
            },
            handler=self._handle_evolve_genome
        ))
        
        # Pattern extraction tool
        self.register_tool(MCPTool(
            name="extract_patterns",
            description="Extract design patterns and principles from code",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to analyze"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language"
                    }
                },
                "required": ["code"]
            },
            handler=self._handle_extract_patterns
        ))
        
        # Memory search tool
        self.register_tool(MCPTool(
            name="search_memory",
            description="Search vector memory for similar patterns",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["code", "pattern", "error", "solution"],
                        "description": "Type of memory to search"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_search_memory
        ))
    
    def _initialize_core_resources(self):
        """Initialize core QLP resources (context) available via MCP"""
        
        # Principle library
        self.register_resource(MCPResource(
            uri="qlp://principles/software-engineering",
            name="Software Engineering Principles",
            description="Curated library of timeless software engineering principles",
            mime_type="application/json",
            content=self._load_principles(),
            metadata={"category": "knowledge", "version": "1.0"}
        ))
        
        # Active genomes
        self.register_resource(MCPResource(
            uri="qlp://genomes/active",
            name="Active Prompt Genomes",
            description="Currently active prompt genomes for all agent roles",
            mime_type="application/json",
            content=self._load_active_genomes(),
            metadata={"category": "evolution", "mutable": True}
        ))
        
        # Performance metrics
        self.register_resource(MCPResource(
            uri="qlp://metrics/performance",
            name="Performance Metrics",
            description="Historical performance metrics and learning data",
            mime_type="application/json",
            content=self._load_performance_metrics(),
            metadata={"category": "analytics", "time_series": True}
        ))
        
        # Design patterns
        self.register_resource(MCPResource(
            uri="qlp://patterns/catalog",
            name="Design Pattern Catalog",
            description="Catalog of design patterns with implementation examples",
            mime_type="application/json",
            content=self._load_design_patterns(),
            metadata={"category": "knowledge", "searchable": True}
        ))
    
    def register_tool(self, tool: MCPTool):
        """Register a tool to be available via MCP"""
        self.tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name}")
    
    def register_resource(self, resource: MCPResource):
        """Register a resource to be available via MCP"""
        self.resources[resource.uri] = resource
        logger.info(f"Registered MCP resource: {resource.uri}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            return await self._handle_initialize(params)
        elif method == "tools/list":
            return await self._handle_list_tools()
        elif method == "tools/call":
            return await self._handle_tool_call(params)
        elif method == "resources/list":
            return await self._handle_list_resources()
        elif method == "resources/read":
            return await self._handle_read_resource(params)
        elif method == "resources/update":
            return await self._handle_update_resource(params)
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session initialization"""
        session_id = params.get("sessionId", "default")
        self.sessions[session_id] = {
            "initialized_at": datetime.utcnow().isoformat(),
            "client_info": params.get("clientInfo", {}),
            "capabilities": params.get("capabilities", {})
        }
        
        return {
            "protocolVersion": "1.0",
            "serverInfo": {
                "name": self.name,
                "version": self.version,
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "resourceSubscriptions": True,
                    "prompts": True
                }
            }
        }
    
    async def _handle_list_tools(self) -> Dict[str, Any]:
        """List all available tools"""
        tools = []
        for tool in self.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters,
                "examples": tool.examples
            })
        
        return {"tools": tools}
    
    async def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        tool = self.tools[tool_name]
        try:
            result = await tool.handler(arguments)
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}", error=str(e))
            return {
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
    
    async def _handle_list_resources(self) -> Dict[str, Any]:
        """List all available resources"""
        resources = []
        for resource in self.resources.values():
            resources.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type,
                "metadata": resource.metadata
            })
        
        return {"resources": resources}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a resource"""
        uri = params.get("uri")
        
        if uri not in self.resources:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Resource not found: {uri}"
                }
            }
        
        resource = self.resources[uri]
        content = resource.content
        
        if isinstance(content, dict):
            content_text = json.dumps(content, indent=2)
        elif isinstance(content, bytes):
            content_text = content.decode('utf-8')
        else:
            content_text = str(content)
        
        return {
            "contents": [{
                "uri": resource.uri,
                "mimeType": resource.mime_type,
                "text": content_text
            }]
        }
    
    async def _handle_update_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update a mutable resource"""
        uri = params.get("uri")
        content = params.get("content")
        
        if uri not in self.resources:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Resource not found: {uri}"
                }
            }
        
        resource = self.resources[uri]
        if not resource.metadata.get("mutable", False):
            return {
                "error": {
                    "code": -32602,
                    "message": f"Resource is not mutable: {uri}"
                }
            }
        
        # Update resource content
        if resource.mime_type == "application/json":
            resource.content = json.loads(content)
        else:
            resource.content = content
        
        return {"success": True}
    
    # Tool handlers
    async def _handle_generate_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation request"""
        from src.agents.ensemble import ProductionCodeGenerator
        
        # Update context with task
        from src.mcp.mcp_api import context_manager
        task_id = context_manager.add_task_context(
            description=args["description"],
            requirements=args.get("requirements", {})
        )
        
        generator = ProductionCodeGenerator()
        result = await generator.generate_production_code(
            description=args["description"],
            requirements=args.get("requirements", {}),
            constraints=args.get("constraints", {})
        )
        
        # Update context with result
        if result.get("status") == "success" and result.get("code"):
            context_manager.add_code_context(
                code=result["code"],
                language="python",
                metadata={
                    "confidence": result.get("confidence", 0),
                    "task_id": task_id,
                    "generator": "ensemble"
                }
            )
        
        return result
    
    async def _handle_evolve_genome(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle genome evolution request"""
        from src.agents.meta_prompts import MetaPromptEngineer
        
        engineer = MetaPromptEngineer()
        await engineer.evolve_population(top_n=5)
        
        return {
            "status": "evolved",
            "role": args["role"],
            "report": engineer.get_evolution_report()
        }
    
    async def _handle_extract_patterns(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pattern extraction request"""
        code = args["code"]
        patterns = []
        
        # Simple pattern detection
        if "class" in code and "def" in code:
            patterns.append("object-oriented")
        if "async def" in code:
            patterns.append("asynchronous")
        if "@" in code:
            patterns.append("decorators")
        if "try:" in code and "except" in code:
            patterns.append("error-handling")
        
        # Update context with the analyzed code
        from src.mcp.mcp_api import context_manager
        context_manager.add_code_context(
            code=code,
            language=args.get("language", "python"),
            metadata={"source": "pattern_extraction", "patterns": patterns}
        )
        
        # Add detected patterns to context
        for pattern in patterns:
            context_manager.add_pattern_context(
                pattern=pattern,
                implementation={"code_snippet": code[:100], "language": args.get("language", "python")}
            )
        
        return {
            "patterns": patterns,
            "language": args.get("language", "python"),
            "context_updated": True
        }
    
    async def _handle_search_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory search request"""
        from src.memory.client import VectorMemoryClient
        from src.common.config import settings
        
        client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)
        results = await client.search_similar(
            query=args["query"],
            collection=args.get("type", "code") + "_patterns",
            limit=args.get("limit", 5)
        )
        
        return {
            "results": results,
            "query": args["query"]
        }
    
    # Resource loaders
    def _load_principles(self) -> Dict[str, List[str]]:
        """Load software engineering principles"""
        from src.agents.meta_prompts.principle_library import PrincipleLibrary
        library = PrincipleLibrary()
        return library.principles
    
    def _load_active_genomes(self) -> Dict[str, Any]:
        """Load active prompt genomes"""
        genome_path = Path("/app/data/prompt_genomes")
        genomes = {}
        
        if genome_path.exists():
            for genome_file in genome_path.glob("*.json"):
                with open(genome_file, 'r') as f:
                    genomes[genome_file.stem] = json.load(f)
        
        return genomes
    
    def _load_performance_metrics(self) -> Dict[str, Any]:
        """Load performance metrics"""
        # This would load from a metrics store
        return {
            "last_updated": datetime.utcnow().isoformat(),
            "average_confidence": 0.812,
            "total_executions": 42,
            "success_rate": 0.89
        }
    
    def _load_design_patterns(self) -> Dict[str, Any]:
        """Load design pattern catalog"""
        return {
            "creational": ["factory", "singleton", "builder"],
            "structural": ["adapter", "decorator", "facade"],
            "behavioral": ["observer", "strategy", "command"],
            "architectural": ["mvc", "mvvm", "clean", "hexagonal"]
        }


class MCPPromptServer(MCPServer):
    """Extended MCP server with prompt management capabilities"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self._initialize_prompts()
    
    def _initialize_prompts(self):
        """Initialize reusable prompts"""
        
        self.register_prompt({
            "name": "explain_code",
            "description": "Explain code with deep reasoning",
            "arguments": [{
                "name": "code",
                "description": "Code to explain",
                "required": True
            }],
            "template": """
Explain this code using first principles thinking:

{code}

Provide:
1. What problem it solves
2. Why this approach was chosen
3. Trade-offs and alternatives
4. How it could be improved
"""
        })
        
        self.register_prompt({
            "name": "refactor_for_principles",
            "description": "Refactor code to better embody principles",
            "arguments": [{
                "name": "code",
                "description": "Code to refactor",
                "required": True
            }, {
                "name": "principles",
                "description": "Principles to apply",
                "required": False
            }],
            "template": """
Refactor this code to better embody software engineering principles:

{code}

Focus on:
{principles}

Show the refactored code and explain each change.
"""
        })
    
    def register_prompt(self, prompt: Dict[str, Any]):
        """Register a reusable prompt"""
        self.prompts[prompt["name"]] = prompt
        logger.info(f"Registered MCP prompt: {prompt['name']}")
