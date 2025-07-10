"""
Vector Memory Service
Manages semantic memory, code patterns, and learning from past executions
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import json
import asyncio
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    UpdateStatus
)
import numpy as np
from openai import AsyncOpenAI, AsyncAzureOpenAI
import hashlib

from src.common.models import (
    ExecutionRequest,
    Task,
    QLCapsule,
    AgentMetrics,
    MemoryEntry
)
from src.common.config import settings

logger = structlog.get_logger()

app = FastAPI(title="Quantum Layer Platform Vector Memory Service", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize clients
if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
    # Use Azure OpenAI if configured
    openai_client = AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
    )
    logger.info(f"Using Azure OpenAI for embeddings: {settings.AZURE_OPENAI_ENDPOINT}")
else:
    # Fall back to OpenAI
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    logger.info("Using OpenAI for embeddings")

qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

# Collection names
COLLECTIONS = {
    "code_patterns": "qlp_code_patterns",
    "agent_decisions": "qlp_agent_decisions", 
    "error_patterns": "qlp_error_patterns",
    "requirements": "qlp_requirements",
    "executions": "qlp_executions"
}

# Vector dimensions (OpenAI embeddings)
VECTOR_DIM = 1536


class VectorMemoryService:
    """Core vector memory functionality"""
    
    def __init__(self):
        self.openai = openai_client
        self.qdrant = qdrant_client
        self.collections = COLLECTIONS
        
    async def initialize_collections(self):
        """Create Qdrant collections if they don't exist"""
        for name, collection_name in self.collections.items():
            try:
                # Check if collection exists
                collections = self.qdrant.get_collections()
                if not any(c.name == collection_name for c in collections.collections):
                    # Create collection
                    self.qdrant.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=VECTOR_DIM,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.info(f"Collection already exists: {collection_name}")
            except Exception as e:
                logger.error(f"Error initializing collection {collection_name}: {e}")
                raise
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI or Azure OpenAI"""
        try:
            # Use deployment name for Azure or model name for OpenAI
            model = "text-embedding-ada-002"
            if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
                # For Azure, use the deployment name
                model = "text-embedding-ada-002"  # Azure deployment name
                
            response = await self.openai.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    async def search_similar_requests(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar past requests"""
        try:
            # Get embedding for the query
            query_vector = await self.get_embedding(description)
            
            # Search in executions collection
            search_result = self.qdrant.search(
                collection_name=self.collections["executions"],
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                score_threshold=0.7  # Only return good matches
            )
            
            results = []
            for point in search_result:
                payload = point.payload
                results.append({
                    "id": point.id,
                    "description": payload.get("description", ""),
                    "tasks": payload.get("tasks", []),
                    "success_rate": payload.get("success_rate", 0.0),
                    "execution_time": payload.get("execution_time", 0),
                    "score": point.score
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar requests: {e}")
            return []
    
    async def search_code_patterns(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar code patterns"""
        try:
            query_vector = await self.get_embedding(query)
            
            search_result = self.qdrant.search(
                collection_name=self.collections["code_patterns"],
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                score_threshold=0.75
            )
            
            results = []
            for point in search_result:
                payload = point.payload
                results.append({
                    "id": point.id,
                    "description": payload.get("description", ""),
                    "code": payload.get("code", ""),
                    "language": payload.get("language", "python"),
                    "usage_count": payload.get("usage_count", 0),
                    "success_rate": payload.get("success_rate", 0.0),
                    "score": point.score
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching code patterns: {e}")
            return []
    
    async def store_decomposition(self, request: ExecutionRequest, tasks: List[Task], dependencies: Dict[str, List[str]]):
        """Store request decomposition for future learning"""
        try:
            # Create a combined text for embedding
            combined_text = f"{request.description}\n\nTasks:\n"
            for task in tasks:
                combined_text += f"- {task.type}: {task.description}\n"
            
            # Get embedding
            embedding = await self.get_embedding(combined_text)
            
            # Generate unique ID
            point_id = str(uuid4())
            
            # Store in executions collection
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "request_id": request.id,
                    "description": request.description,
                    "tasks": [{"id": t.id, "type": t.type, "description": t.description} for t in tasks],
                    "dependencies": dependencies,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "tenant_id": request.tenant_id,
                    "user_id": request.user_id
                }
            )
            
            self.qdrant.upsert(
                collection_name=self.collections["executions"],
                points=[point]
            )
            
            logger.info(f"Stored decomposition for request {request.id}")
            
        except Exception as e:
            logger.error(f"Error storing decomposition: {e}")
            raise
    
    async def get_task_performance(self, task_type: str, complexity: str) -> Optional[Dict[str, Any]]:
        """Get historical performance data for task type"""
        try:
            # Search for similar tasks
            query = f"task_type:{task_type} complexity:{complexity}"
            
            result = self.qdrant.scroll(
                collection_name=self.collections["agent_decisions"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="task_type",
                            match=MatchValue(value=task_type)
                        ),
                        FieldCondition(
                            key="complexity",
                            match=MatchValue(value=complexity)
                        )
                    ]
                ),
                limit=100,
                with_payload=True
            )
            
            if not result[0]:
                return None
            
            # Aggregate performance data
            performances = []
            for point in result[0]:
                payload = point.payload
                performances.append({
                    "tier": payload.get("agent_tier"),
                    "success": payload.get("success", False),
                    "execution_time": payload.get("execution_time", 0)
                })
            
            # Calculate best tier
            tier_stats = {}
            for perf in performances:
                tier = perf["tier"]
                if tier not in tier_stats:
                    tier_stats[tier] = {"success_count": 0, "total_count": 0, "total_time": 0}
                
                tier_stats[tier]["total_count"] += 1
                if perf["success"]:
                    tier_stats[tier]["success_count"] += 1
                tier_stats[tier]["total_time"] += perf["execution_time"]
            
            # Find optimal tier
            best_tier = None
            best_success_rate = 0
            
            for tier, stats in tier_stats.items():
                success_rate = stats["success_count"] / stats["total_count"]
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_tier = tier
            
            return {
                "optimal_tier": best_tier,
                "success_rate": best_success_rate,
                "sample_size": len(performances),
                "tier_stats": tier_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting task performance: {e}")
            return None
    
    async def store_capsule(self, capsule: QLCapsule):
        """Store a QLCapsule with its code patterns"""
        try:
            # Store each code file as a pattern
            for filename, code in capsule.source_code.items():
                # Create description
                description = f"Code from {filename} for request: {capsule.request_id}"
                
                # Get embedding
                embedding = await self.get_embedding(f"{description}\n\n{code}")
                
                # Store as code pattern
                point = PointStruct(
                    id=str(uuid4()),
                    vector=embedding,
                    payload={
                        "capsule_id": capsule.id,
                        "request_id": capsule.request_id,
                        "filename": filename,
                        "description": description,
                        "code": code,
                        "language": self._detect_language(filename),
                        "validation_score": capsule.validation_report.confidence_score if capsule.validation_report and capsule.validation_report.confidence_score is not None else 0.5,
                        "created_at": capsule.created_at,
                        "usage_count": 0,
                        "success_rate": capsule.validation_report.confidence_score if capsule.validation_report and capsule.validation_report.confidence_score is not None else 0.5
                    }
                )
                
                self.qdrant.upsert(
                    collection_name=self.collections["code_patterns"],
                    points=[point]
                )
            
            logger.info(f"Stored capsule {capsule.id} with {len(capsule.source_code)} code patterns")
            
        except Exception as e:
            logger.error(f"Error storing capsule: {e}")
            raise
    
    async def store_agent_metrics(self, metrics: AgentMetrics):
        """Store agent performance metrics"""
        try:
            # Create text for embedding
            text = f"Agent {metrics.tier} for {metrics.task_type}: success_rate={metrics.success_rate}"
            embedding = await self.get_embedding(text)
            
            # Store metrics
            point = PointStruct(
                id=str(uuid4()),
                vector=embedding,
                payload={
                    "agent_id": metrics.agent_id,
                    "tier": metrics.tier,
                    "task_type": metrics.task_type,
                    "success_rate": metrics.success_rate,
                    "average_execution_time": metrics.average_execution_time,
                    "total_executions": metrics.total_executions,
                    "last_updated": metrics.last_updated
                }
            )
            
            self.qdrant.upsert(
                collection_name=self.collections["agent_decisions"],
                points=[point]
            )
            
            logger.info(f"Stored metrics for agent {metrics.agent_id}")
            
        except Exception as e:
            logger.error(f"Error storing agent metrics: {e}")
            raise
    
    async def learn_from_error(self, error_context: Dict[str, Any]):
        """Store error patterns for future prevention"""
        try:
            # Create error description
            error_text = f"""
Error Type: {error_context.get('error_type', 'Unknown')}
Task: {error_context.get('task_description', '')}
Error Message: {error_context.get('error_message', '')}
Stack Trace: {error_context.get('stack_trace', '')[:500]}
"""
            
            # Get embedding
            embedding = await self.get_embedding(error_text)
            
            # Store error pattern
            point = PointStruct(
                id=str(uuid4()),
                vector=embedding,
                payload={
                    **error_context,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "occurrence_count": 1
                }
            )
            
            self.qdrant.upsert(
                collection_name=self.collections["error_patterns"],
                points=[point]
            )
            
            logger.info("Stored error pattern for learning")
            
        except Exception as e:
            logger.error(f"Error storing error pattern: {e}")
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin'
        }
        
        for ext, lang in extension_map.items():
            if filename.endswith(ext):
                return lang
        
        return 'unknown'


# Initialize service
memory_service = VectorMemoryService()


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize collections on startup"""
    await memory_service.initialize_collections()


@app.post("/search/requests")
async def search_requests(query: Dict[str, Any]):
    """Search for similar past requests"""
    description = query.get("description", "")
    limit = query.get("limit", 5)
    
    results = await memory_service.search_similar_requests(description, limit)
    return results


@app.post("/search/code")
async def search_code(query: Dict[str, Any]):
    """Search for similar code patterns"""
    search_query = query.get("query", "")
    limit = query.get("limit", 5)
    
    results = await memory_service.search_code_patterns(search_query, limit)
    return results


@app.post("/store/decomposition")
async def store_decomposition(data: Dict[str, Any]):
    """Store request decomposition"""
    request = ExecutionRequest(**data["request"])
    tasks = [Task(**t) for t in data["tasks"]]
    dependencies = data["dependencies"]
    
    await memory_service.store_decomposition(request, tasks, dependencies)
    return {"status": "stored"}


@app.get("/performance/task")
async def get_task_performance(
    type: str = Query(..., description="Task type"),
    complexity: str = Query(..., description="Task complexity")
):
    """Get historical performance for task type"""
    result = await memory_service.get_task_performance(type, complexity)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="No performance data found")


@app.post("/store/capsule")
async def store_capsule(capsule_data: Dict[str, Any]):
    """Store a QLCapsule"""
    try:
        capsule = QLCapsule(**capsule_data)
        await memory_service.store_capsule(capsule)
        return {"status": "stored", "capsule_id": capsule.id}
    except ValueError as e:
        logger.error(f"Invalid capsule data: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid capsule data: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to store capsule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store capsule: {str(e)}")


@app.post("/store/metrics")
async def store_metrics(metrics_data: Dict[str, Any]):
    """Store agent performance metrics"""
    metrics = AgentMetrics(**metrics_data)
    await memory_service.store_agent_metrics(metrics)
    return {"status": "stored"}


@app.post("/store/error")
async def store_error(error_context: Dict[str, Any]):
    """Store error pattern for learning"""
    await memory_service.learn_from_error(error_context)
    return {"status": "stored"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        collections = memory_service.qdrant.get_collections()
        return {
            "status": "healthy",
            "service": "vector-memory",
            "collections": len(collections.collections),
            "qdrant_status": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "vector-memory",
            "error": str(e)
        }


@app.get("/stats")
async def get_stats():
    """Get memory statistics"""
    try:
        stats = {}
        for name, collection_name in COLLECTIONS.items():
            collection_info = memory_service.qdrant.get_collection(collection_name)
            stats[name] = {
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count
            }
        
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/performance/task")
async def get_task_performance(
    type: str, 
    complexity: str = "medium"
):
    """Get performance metrics for a task type"""
    try:
        performance = await memory_service.get_task_performance(type, complexity)
        if performance:
            return performance
        else:
            # Return default performance if no data exists
            return {
                "optimal_tier": "T0",
                "success_rate": 0.8,
                "sample_size": 0,
                "tier_stats": {}
            }
    except Exception as e:
        logger.error(f"Error getting task performance: {e}")
        # Return default on error instead of 404
        return {
            "optimal_tier": "T0",
            "success_rate": 0.8,
            "sample_size": 0,
            "tier_stats": {}
        }




@app.post("/patterns/code")
async def store_code_pattern(pattern: Dict[str, Any]):
    """Store a code pattern"""
    try:
        content = pattern.get("content", "")
        metadata = pattern.get("metadata", {})
        
        # Get embedding
        embedding = await memory_service.get_embedding(content)
        
        # Store pattern
        point = PointStruct(
            id=str(uuid4()),
            vector=embedding,
            payload={
                "content": content,
                "type": "code_pattern",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
        )
        
        memory_service.qdrant.upsert(
            collection_name=COLLECTIONS["code_patterns"],
            points=[point]
        )
        
        return {"status": "stored", "id": point.id}
        
    except Exception as e:
        logger.error(f"Error storing code pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/patterns")
async def search_patterns(query: Dict[str, Any]):
    """Search for patterns"""
    search_query = query.get("query", "")
    limit = query.get("limit", 5)
    
    results = await memory_service.search_code_patterns(search_query, limit)
    return {"results": results}


@app.post("/patterns/execution")
async def store_execution_pattern(data: Dict[str, Any]):
    """Store execution pattern"""
    try:
        content = data.get("content", {})
        metadata = data.get("metadata", {})
        
        # Create text representation
        text = f"Task: {content.get('task', {}).get('description', '')}"
        text += f"\nResult: {content.get('result', {}).get('status', '')}"
        
        # Get embedding
        embedding = await memory_service.get_embedding(text)
        
        # Store pattern
        point = PointStruct(
            id=str(uuid4()),
            vector=embedding,
            payload={
                **content,
                **metadata,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        memory_service.qdrant.upsert(
            collection_name=COLLECTIONS["executions"],
            points=[point]
        )
        
        return {"status": "stored"}
        
    except Exception as e:
        logger.error(f"Error storing execution pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/patterns/validation")
async def store_validation_pattern(data: Dict[str, Any]):
    """Store validation pattern"""
    try:
        content = data.get("content", {})
        metadata = data.get("metadata", {})
        
        # Create text representation
        text = f"Validation for task: {content.get('task_id', '')}"
        text += f"\nStatus: {content.get('validation', {}).get('overall_status', '')}"
        
        # Get embedding
        embedding = await memory_service.get_embedding(text)
        
        # Store pattern
        point = PointStruct(
            id=str(uuid4()),
            vector=embedding,
            payload={
                **content,
                **metadata,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        memory_service.qdrant.upsert(
            collection_name=COLLECTIONS["agent_decisions"],
            points=[point]
        )
        
        return {"status": "stored"}
        
    except Exception as e:
        logger.error(f"Error storing validation pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/patterns/capsule")
async def store_capsule_pattern(data: Dict[str, Any]):
    """Store capsule pattern"""
    try:
        content = json.loads(data.get("content", "{}"))
        metadata = data.get("metadata", {})
        
        # Create text representation
        text = f"Capsule: {content.get('id', '')}"
        text += f"\nRequest: {content.get('request_id', '')}"
        text += f"\nFiles: {len(content.get('source_code', {}))}"
        
        # Get embedding
        embedding = await memory_service.get_embedding(text)
        
        # Store pattern
        point = PointStruct(
            id=str(uuid4()),
            vector=embedding,
            payload={
                "capsule": content,
                **metadata,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        memory_service.qdrant.upsert(
            collection_name=COLLECTIONS["executions"],
            points=[point]
        )
        
        return {"status": "stored"}
        
    except Exception as e:
        logger.error(f"Error storing capsule pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/store/execution")
async def store_execution(data: Dict[str, Any]):
    """Store task execution for learning"""
    return await store_execution_pattern(data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
