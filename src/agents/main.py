"""
Agent Factory Service
Manages the creation and execution of different agent tiers
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
import structlog

from src.common.models import (
    Task,
    TaskResult,
    AgentTier,
    TaskStatus,
    AgentMetrics
)
from src.common.config import settings
from src.memory.client import VectorMemoryClient
from src.agents.base_agents import Agent, T0Agent, T1Agent, T2Agent, T3Agent

# Import ensemble components - do this after base agents to avoid circular import
try:
    from src.agents.ensemble import (
        ProductionCodeGenerator,
        EnsembleOrchestrator,
        EnsembleConfiguration,
        VotingStrategy
    )
    ENSEMBLE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Ensemble agents not available: {e}")
    ENSEMBLE_AVAILABLE = False

logger = structlog.get_logger()

app = FastAPI(title="Quantum Layer Platform Agent Factory", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize clients
memory_client = VectorMemoryClient(settings.VECTOR_MEMORY_URL)

# MCP Integration
try:
    from src.mcp.mcp_api import mcp_app
    from src.mcp.context_enhancement import (
        enhance_request_with_mcp_context,
        update_mcp_from_result,
        get_context_manager
    )
    app.mount("/mcp", mcp_app)
    logger.info("MCP endpoints mounted at /mcp")
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCP module not available, skipping MCP integration")
    MCP_AVAILABLE = False


class AgentExecutionRequest(BaseModel):
    """Request to execute a task with an agent"""
    task: Task
    tier: str  # Accept string and convert to AgentTier
    context: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(default=300, description="Timeout in seconds")


class AgentFactory:
    """Factory for creating agents based on tier and task requirements"""
    
    def __init__(self):
        self.active_agents: Dict[str, Agent] = {}
        self.metrics: Dict[str, AgentMetrics] = {}
        
    def create_agent(self, tier: AgentTier) -> Agent:
        """Create an agent of the specified tier"""
        agent_id = str(uuid4())
        
        if tier == AgentTier.T0:
            agent = T0Agent(agent_id)
        elif tier == AgentTier.T1:
            agent = T1Agent(agent_id)
        elif tier == AgentTier.T2:
            agent = T2Agent(agent_id)
        elif tier == AgentTier.T3:
            agent = T3Agent(agent_id)
        else:
            raise ValueError(f"Unknown agent tier: {tier}")
        
        self.active_agents[agent_id] = agent
        logger.info(f"Created agent", agent_id=agent_id, tier=tier)
        
        return agent
    
    async def execute_task(self, task: Task, tier: AgentTier, context: Dict[str, Any]) -> TaskResult:
        """Execute a task using an agent of the specified tier"""
        agent = self.create_agent(tier)
        
        try:
            result = await agent.execute(task, context)
            
            # Update metrics
            await self._update_metrics(agent, task, result)
            
            return result
            
        finally:
            # Clean up agent
            del self.active_agents[agent.agent_id]
    
    async def _update_metrics(self, agent: Agent, task: Task, result: TaskResult):
        """Update agent performance metrics"""
        metrics_key = f"{agent.tier}_{task.type}"
        
        if metrics_key not in self.metrics:
            self.metrics[metrics_key] = AgentMetrics(
                agent_id=agent.agent_id,
                tier=agent.tier,
                task_type=task.type,
                success_rate=0.0,
                average_execution_time=0.0,
                total_executions=0,
                last_updated=datetime.utcnow().isoformat()
            )
        
        metrics = self.metrics[metrics_key]
        
        # Update metrics
        success = 1 if result.status == TaskStatus.COMPLETED else 0
        metrics.total_executions += 1
        metrics.success_rate = (
            (metrics.success_rate * (metrics.total_executions - 1) + success) / 
            metrics.total_executions
        )
        metrics.average_execution_time = (
            (metrics.average_execution_time * (metrics.total_executions - 1) + result.execution_time) /
            metrics.total_executions
        )
        metrics.last_updated = datetime.utcnow().isoformat()
        
        # Store in vector memory for future optimization
        await memory_client.store_agent_metrics(metrics)


# Global factory instance
agent_factory = AgentFactory()

# Production code generator with ensemble (if available)
if ENSEMBLE_AVAILABLE:
    try:
        from advanced_integration import AdvancedProductionGenerator
        production_generator = AdvancedProductionGenerator()
        logger.info("✅ Advanced strategies enabled successfully!")
    except ImportError:
        logger.warning("Advanced integration not found, using basic generator")
        production_generator = ProductionCodeGenerator()
else:
    production_generator = None


# API Endpoints
@app.post("/execute")
async def execute_task(request: AgentExecutionRequest):
    """Execute a task using the appropriate agent"""
    try:
        # Convert string tier to AgentTier enum
        if isinstance(request.tier, str):
            tier = AgentTier(request.tier)
        else:
            tier = request.tier

        result = await agent_factory.execute_task(
            request.task,
            tier,
            request.context
        )
        return JSONResponse(content=jsonable_encoder(result))
        
    except Exception as e:
        logger.error("Task execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get agent performance metrics"""
    return {
        "metrics": [m.dict() for m in agent_factory.metrics.values()],
        "active_agents": len(agent_factory.active_agents)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agent-factory",
        "active_agents": len(agent_factory.active_agents),
        "ensemble_available": ENSEMBLE_AVAILABLE
    }


@app.post("/test/simple")
async def test_simple_execution():
    """Test endpoint for simple task execution"""
    # Create a simple test task
    test_task = Task(
        id="test-task-001",
        type="code_generation",
        description="Write a Python function that returns 'Hello, World!'",
        complexity="trivial"
    )
    
    try:
        # Execute with T0 agent
        result = await agent_factory.execute_task(
            test_task,
            AgentTier.T0,
            {}
        )
        
        return JSONResponse(content=jsonable_encoder(result))
        
    except Exception as e:
        logger.error("Test execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Ensemble endpoints (only if ensemble is available)
if ENSEMBLE_AVAILABLE:
    
    class EnsembleExecutionRequest(BaseModel):
        """Request for ensemble execution"""
        description: str
        requirements: Optional[Dict[str, Any]] = None
        constraints: Optional[Dict[str, Any]] = None
        ensemble_config: Optional[Dict[str, Any]] = None


    @app.post("/execute/ensemble")
    async def execute_ensemble(request: EnsembleExecutionRequest):
        """Execute task using ensemble of agents for production-grade code"""
        try:
            # Enhance request with MCP context if available
            request_dict = request.dict()
            if MCP_AVAILABLE:
                request_dict = enhance_request_with_mcp_context(request_dict)
            
            # Use custom config if provided
            if request.ensemble_config:
                logger.info("Using custom ensemble config", config=request.ensemble_config)
                config = EnsembleConfiguration(**request.ensemble_config)
                orchestrator = EnsembleOrchestrator(config)
                generator = ProductionCodeGenerator()
                generator.orchestrator = orchestrator
            else:
                logger.info("Using advanced production generator", 
                           generator_type=type(production_generator).__name__)
                generator = production_generator
            
            # Generate production code
            result = await generator.generate_production_code(
                description=request_dict['description'],
                requirements=request_dict.get('requirements'),
                constraints=request_dict.get('constraints')
            )
            
            # Update MCP context with result if available
            if MCP_AVAILABLE:
                # Handle both dict and model results
                if hasattr(result, 'dict'):
                    result_dict = result.dict()
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    result_dict = jsonable_encoder(result)
                
                result_dict = update_mcp_from_result(result_dict, "ensemble")
                return JSONResponse(content=result_dict)
            
            return JSONResponse(content=jsonable_encoder(result))
            
        except Exception as e:
            logger.error("Ensemble execution failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/execute/production")
    async def execute_production(request: EnsembleExecutionRequest):
        """Alias for ensemble execution with production focus"""
        # Add production-specific requirements
        if request.requirements is None:
            request.requirements = {}
        
        request.requirements.update({
            "code_quality": "production",
            "testing": "comprehensive",
            "error_handling": "robust",
            "documentation": "detailed",
            "security": "production-grade"
        })
        
        # Add MCP context flag without forcing ensemble_config
        # This allows the advanced generator to be used
        if MCP_AVAILABLE and request.ensemble_config:
            request.ensemble_config['use_mcp_context'] = True
        
        return await execute_ensemble(request)


    @app.get("/ensemble/strategies")
    async def get_ensemble_strategies():
        """Get available ensemble voting strategies"""
        return {
            "strategies": [
                {
                    "name": strategy.value,
                    "description": {
                        VotingStrategy.MAJORITY: "Simple majority voting on outputs",
                        VotingStrategy.WEIGHTED: "Weighted voting based on agent roles",
                        VotingStrategy.CONFIDENCE_BASED: "Synthesis based on confidence scores",
                        VotingStrategy.QUALITY_WEIGHTED: "Weighted by quality metrics",
                        VotingStrategy.ADAPTIVE: "Adaptive strategy based on task characteristics"
                    }[strategy]
                }
                for strategy in VotingStrategy
            ],
            "default": VotingStrategy.ADAPTIVE
        }


    @app.get("/ensemble/metrics")
    async def get_ensemble_metrics():
        """Get ensemble performance metrics"""
        try:
            # Get performance history from the production generator
            if hasattr(production_generator.orchestrator, 'performance_history'):
                history = production_generator.orchestrator.performance_history
                
                # Calculate aggregate metrics
                metrics = {}
                for role, entries in history.items():
                    if entries:
                        metrics[role] = {
                            "total_executions": len(entries),
                            "avg_confidence": sum(e["confidence"] for e in entries) / len(entries),
                            "avg_validation_score": sum(e["validation_score"] for e in entries) / len(entries),
                            "avg_final_score": sum(e["final_score"] for e in entries) / len(entries),
                            "avg_execution_time": sum(e["execution_time"] for e in entries) / len(entries)
                        }
                
                return {
                    "ensemble_metrics": metrics,
                    "total_ensemble_executions": sum(len(entries) for entries in history.values())
                }
            else:
                return {
                    "ensemble_metrics": {},
                    "total_ensemble_executions": 0
                }
        except Exception as e:
            logger.error("Failed to get ensemble metrics", error=str(e))
            return {
                "ensemble_metrics": {},
                "total_ensemble_executions": 0,
                "error": str(e)
            }


    @app.post("/execute/advanced/{strategy}")
    async def execute_with_strategy(strategy: str, request: EnsembleExecutionRequest):
        """Execute with a specific advanced strategy"""
        try:
            from src.agents.advanced_generation import EnhancedCodeGenerator, GenerationStrategy
            
            # Validate strategy
            try:
                selected_strategy = GenerationStrategy(strategy.lower())
            except ValueError:
                raise HTTPException(400, f"Invalid strategy: {strategy}")
            
            generator = EnhancedCodeGenerator()
            result = await generator.generate_enhanced(
                prompt=request.description,
                strategy=selected_strategy,
                requirements=request.requirements or {},
                constraints=request.constraints or {}
            )
            
            return JSONResponse(content={
                "code": result.code,
                "tests": result.tests,
                "documentation": result.documentation,
                "confidence": result.confidence,
                "validation_score": result.validation_score,
                "strategy_used": strategy,
                "patterns_applied": result.patterns_applied,
                "improvements_made": result.improvements_made
            })
            
        except Exception as e:
            logger.error(f"Advanced strategy execution failed: {str(e)}")
            raise HTTPException(500, str(e))


    @app.get("/strategies")
    async def list_strategies():
        """List all available strategies with descriptions"""
        from src.agents.advanced_generation import GenerationStrategy
        
        strategies = {
            "TEST_DRIVEN": "Generates tests first, then code (95% confidence)",
            "MULTI_MODEL": "Uses 4 AI models for consensus (85% confidence)",
            "STATIC_ANALYSIS": "Iterative improvement with 5 analyzers",
            "EXECUTION_BASED": "Validates through actual execution",
            "PATTERN_BASED": "Uses proven patterns from memory",
            "INCREMENTAL": "Builds step-by-step with validation",
            "SELF_HEALING": "Adds retry logic and fault tolerance",
            "CONTEXT_AWARE": "Integrates with system context"
        }
        
        return {"strategies": strategies, "recommended": "TEST_DRIVEN"}

else:
    # Ensemble not available - provide stub endpoints
    @app.post("/execute/ensemble")
    async def execute_ensemble_stub():
        """Ensemble execution not available"""
        raise HTTPException(
            status_code=503, 
            detail="Ensemble execution not available. Check service logs."
        )
    
    @app.post("/execute/production")
    async def execute_production_stub():
        """Production execution not available"""
        raise HTTPException(
            status_code=503, 
            detail="Production execution not available. Check service logs."
        )
    
    @app.get("/ensemble/strategies")
    async def get_ensemble_strategies_stub():
        """Ensemble strategies not available"""
        return {
            "error": "Ensemble not available",
            "strategies": [],
            "default": None
        }
    
    @app.get("/ensemble/metrics")
    async def get_ensemble_metrics_stub():
        """Ensemble metrics not available"""
        return {
            "error": "Ensemble not available",
            "ensemble_metrics": {},
            "total_ensemble_executions": 0
        }


# Error handling metrics endpoint
@app.get("/error-metrics")
async def get_error_metrics():
    """Get error handling and circuit breaker metrics"""
    # Import error handler inside function to ensure it's loaded
    from src.common.error_handling import error_handler
    
    metrics = error_handler.get_metrics()
    
    # Add service-specific information
    metrics["service"] = "agent_factory"
    metrics["timestamp"] = datetime.utcnow().isoformat()
    
    # Add health status based on circuit breakers
    open_circuits = [
        name for name, cb in metrics["circuit_breakers"].items() 
        if cb["state"] == "open"
    ]
    metrics["health_status"] = "degraded" if open_circuits else "healthy"
    metrics["open_circuits"] = open_circuits
    
    return metrics


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
