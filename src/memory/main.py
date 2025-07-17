"""
Vector Memory Service
Manages semantic memory, code patterns, and learning from past executions
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import json
import asyncio
from uuid import uuid4, UUID

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

# Initialize Qdrant client with cloud credentials if available
import os

qdrant_url = os.getenv('QDRANT_CLOUD_URL') or settings.QDRANT_URL
qdrant_api_key = os.getenv('QDRANT_CLOUD_API_KEY') or settings.QDRANT_API_KEY

logger.info(f"Initializing Qdrant client with URL: {qdrant_url}")
qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

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
        """Create Qdrant collections if they don't exist with optimized payload indexing"""
        from qdrant_client.models import PayloadSchemaType
        
        # Define payload indexes for each collection type
        collection_indexes = {
            "code_patterns": [
                ("language", PayloadSchemaType.KEYWORD),
                ("capsule_id", PayloadSchemaType.KEYWORD),
                ("request_id", PayloadSchemaType.KEYWORD),
                ("validation_score", PayloadSchemaType.FLOAT),
                ("created_at", PayloadSchemaType.DATETIME),
                ("usage_count", PayloadSchemaType.INTEGER),
                ("success_rate", PayloadSchemaType.FLOAT)
            ],
            "agent_decisions": [
                ("task_type", PayloadSchemaType.KEYWORD),
                ("complexity", PayloadSchemaType.KEYWORD),
                ("agent_tier", PayloadSchemaType.KEYWORD),
                ("tier", PayloadSchemaType.KEYWORD),
                ("success_rate", PayloadSchemaType.FLOAT),
                ("execution_time", PayloadSchemaType.FLOAT),
                ("created_at", PayloadSchemaType.DATETIME)
            ],
            "error_patterns": [
                ("error_type", PayloadSchemaType.KEYWORD),
                ("task_id", PayloadSchemaType.KEYWORD),
                ("agent_id", PayloadSchemaType.KEYWORD),
                ("created_at", PayloadSchemaType.DATETIME),
                ("occurrence_count", PayloadSchemaType.INTEGER)
            ],
            "requirements": [
                ("tenant_id", PayloadSchemaType.KEYWORD),
                ("user_id", PayloadSchemaType.KEYWORD),
                ("created_at", PayloadSchemaType.DATETIME),
                ("complexity", PayloadSchemaType.KEYWORD),
                ("status", PayloadSchemaType.KEYWORD)
            ],
            "executions": [
                ("request_id", PayloadSchemaType.KEYWORD),
                ("tenant_id", PayloadSchemaType.KEYWORD),
                ("user_id", PayloadSchemaType.KEYWORD),
                ("created_at", PayloadSchemaType.DATETIME),
                ("success_rate", PayloadSchemaType.FLOAT),
                ("execution_time", PayloadSchemaType.FLOAT),
                ("capsule_id", PayloadSchemaType.KEYWORD)
            ]
        }
        
        for name, collection_name in self.collections.items():
            try:
                # Check if collection exists
                collections = self.qdrant.get_collections()
                collection_exists = any(c.name == collection_name for c in collections.collections)
                
                if not collection_exists:
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
                
                # Create or update payload indexes
                if name in collection_indexes:
                    for field_name, field_type in collection_indexes[name]:
                        try:
                            self.qdrant.create_payload_index(
                                collection_name=collection_name,
                                field_name=field_name,
                                field_schema=field_type
                            )
                            logger.info(f"Created/updated index for {field_name} in {collection_name}")
                        except Exception as idx_error:
                            # Index might already exist, log but continue
                            logger.debug(f"Index {field_name} may already exist: {idx_error}")
                            
            except Exception as e:
                logger.error(f"Error initializing collection {collection_name}: {e}")
                raise
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI or Azure OpenAI"""
        try:
            # Use deployment name for Azure or model name for OpenAI
            if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
                # For Azure, use the deployment name from your Azure OpenAI resource
                model = "text-embedding-ada-002"  # Your Azure deployment name
            else:
                # For OpenAI, use the model name
                model = "text-embedding-ada-002"
                
            response = await self.openai.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    async def search_similar_requests(self, description: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar past requests with optional filtering"""
        try:
            # Get embedding for the query
            query_vector = await self.get_embedding(description)
            
            # Build filter conditions if provided
            filter_conditions = None
            if filters:
                must_conditions = []
                for key, value in filters.items():
                    if value is not None:
                        must_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                if must_conditions:
                    filter_conditions = Filter(must=must_conditions)
            
            # Search in executions collection with filters
            search_result = self.qdrant.search(
                collection_name=self.collections["executions"],
                query_vector=query_vector,
                query_filter=filter_conditions,
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
                    "score": point.score,
                    "tenant_id": payload.get("tenant_id"),
                    "user_id": payload.get("user_id"),
                    "created_at": payload.get("created_at")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar requests: {e}")
            return []
    
    async def search_code_patterns(self, query: str, limit: int = 5, language: Optional[str] = None, min_success_rate: Optional[float] = None) -> List[Dict[str, Any]]:
        """Search for similar code patterns with language and quality filtering"""
        try:
            query_vector = await self.get_embedding(query)
            
            # Build filter conditions
            must_conditions = []
            if language:
                must_conditions.append(
                    FieldCondition(
                        key="language",
                        match=MatchValue(value=language)
                    )
                )
            if min_success_rate is not None:
                must_conditions.append(
                    FieldCondition(
                        key="success_rate",
                        range={"gte": min_success_rate}
                    )
                )
            
            filter_conditions = Filter(must=must_conditions) if must_conditions else None
            
            search_result = self.qdrant.search(
                collection_name=self.collections["code_patterns"],
                query_vector=query_vector,
                query_filter=filter_conditions,
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
                    "score": point.score,
                    "capsule_id": payload.get("capsule_id"),
                    "created_at": payload.get("created_at")
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
    
    async def optimize_collections(self):
        """Optimize existing collections by updating configuration and indexes"""
        from qdrant_client.models import OptimizersConfig, PayloadSchemaType
        
        optimizers_config = OptimizersConfig(
            indexing_threshold=1000,  # Start indexing after 1000 vectors
            memmap_threshold=50000,   # Use memory mapping for large collections
            default_segment_number=4,  # Parallel segments for better performance
            max_segment_size=200000,  # Maximum vectors per segment
            flush_interval_sec=5      # Flush to disk every 5 seconds
        )
        
        for name, collection_name in self.collections.items():
            try:
                # Update collection configuration
                self.qdrant.update_collection(
                    collection_name=collection_name,
                    optimizer_config=optimizers_config
                )
                logger.info(f"Updated optimizer config for {collection_name}")
                
                # Force re-indexing if needed
                collection_info = self.qdrant.get_collection(collection_name)
                if collection_info.points_count > 1000:
                    # Recreate indexes to ensure optimization
                    logger.info(f"Re-indexing {collection_name} with {collection_info.points_count} points")
                    
            except Exception as e:
                logger.error(f"Error optimizing collection {collection_name}: {e}")
    
    async def batch_store_code_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch store multiple code patterns for efficiency"""
        try:
            points = []
            successful_ids = []
            failed_patterns = []
            
            # Process patterns in parallel for embedding generation
            import asyncio
            
            async def process_pattern(pattern):
                try:
                    # Extract data
                    code = pattern.get("code", "")
                    description = pattern.get("description", "")
                    language = pattern.get("language", "python")
                    metadata = pattern.get("metadata", {})
                    
                    # Generate embedding
                    embedding_text = f"{description}\n\n{code}"
                    embedding = await self.get_embedding(embedding_text)
                    
                    # Create point
                    point_id = str(uuid4())
                    point = PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "description": description,
                            "code": code,
                            "language": language,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "usage_count": 0,
                            "success_rate": metadata.get("success_rate", 0.5),
                            **metadata
                        }
                    )
                    
                    return point_id, point, None
                except Exception as e:
                    return None, None, {"pattern": pattern, "error": str(e)}
            
            # Process all patterns concurrently
            tasks = [process_pattern(p) for p in patterns]
            results = await asyncio.gather(*tasks)
            
            # Collect successful points and failures
            for point_id, point, error in results:
                if point:
                    points.append(point)
                    successful_ids.append(point_id)
                else:
                    failed_patterns.append(error)
            
            # Batch insert successful points
            if points:
                self.qdrant.upsert(
                    collection_name=self.collections["code_patterns"],
                    points=points,
                    wait=True  # Wait for operation to complete
                )
                logger.info(f"Batch stored {len(points)} code patterns")
            
            return {
                "success": len(successful_ids),
                "failed": len(failed_patterns),
                "ids": successful_ids,
                "errors": failed_patterns
            }
            
        except Exception as e:
            logger.error(f"Error in batch store: {e}")
            raise
    
    async def batch_search_patterns(self, queries: List[str], limit: int = 5) -> List[List[Dict[str, Any]]]:
        """Batch search for multiple queries efficiently"""
        try:
            # Generate embeddings for all queries in parallel
            tasks = [self.get_embedding(q) for q in queries]
            query_vectors = await asyncio.gather(*tasks)
            
            # Perform batch search
            from qdrant_client.models import SearchRequest
            
            search_requests = [
                SearchRequest(
                    vector=vector,
                    limit=limit,
                    with_payload=True,
                    score_threshold=0.7
                )
                for vector in query_vectors
            ]
            
            # Execute batch search
            batch_results = self.qdrant.search_batch(
                collection_name=self.collections["code_patterns"],
                requests=search_requests
            )
            
            # Process results
            all_results = []
            for query_results in batch_results:
                results = []
                for point in query_results:
                    payload = point.payload
                    results.append({
                        "id": point.id,
                        "description": payload.get("description", ""),
                        "code": payload.get("code", ""),
                        "language": payload.get("language", "python"),
                        "score": point.score
                    })
                all_results.append(results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            return [[] for _ in queries]  # Return empty results for each query
    
    async def batch_update_metrics(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch update metrics for multiple patterns"""
        try:
            success_count = 0
            failed_count = 0
            
            # Group updates by operation type
            from qdrant_client.models import UpdateOperation, SetPayload
            
            for update in updates:
                try:
                    point_id = update.get("id")
                    if not point_id:
                        failed_count += 1
                        continue
                    
                    # Prepare payload updates
                    payload_updates = {}
                    
                    if "increment_usage" in update:
                        # For incrementing usage, we need to fetch current value
                        points = self.qdrant.retrieve(
                            collection_name=self.collections["code_patterns"],
                            ids=[point_id],
                            with_payload=True
                        )
                        if points:
                            current_usage = points[0].payload.get("usage_count", 0)
                            payload_updates["usage_count"] = current_usage + 1
                    
                    if "success_rate" in update:
                        payload_updates["success_rate"] = update["success_rate"]
                    
                    if "last_used" in update:
                        payload_updates["last_used"] = update["last_used"]
                    
                    # Apply updates
                    if payload_updates:
                        self.qdrant.set_payload(
                            collection_name=self.collections["code_patterns"],
                            payload=payload_updates,
                            points=[point_id]
                        )
                        success_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to update point {point_id}: {e}")
                    failed_count += 1
            
            return {
                "success": success_count,
                "failed": failed_count
            }
            
        except Exception as e:
            logger.error(f"Error in batch update metrics: {e}")
            raise


# Initialize service
memory_service = VectorMemoryService()


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize collections on startup"""
    await memory_service.initialize_collections()


@app.post("/search/requests")
async def search_requests(query: Dict[str, Any]):
    """Search for similar past requests with optional filtering"""
    description = query.get("description", "")
    limit = query.get("limit", 5)
    filters = query.get("filters", {})
    
    results = await memory_service.search_similar_requests(description, limit, filters)
    return results


@app.post("/search/code")
async def search_code(query: Dict[str, Any]):
    """Search for similar code patterns with filtering"""
    search_query = query.get("query", "")
    limit = query.get("limit", 5)
    language = query.get("language")
    min_success_rate = query.get("min_success_rate")
    
    results = await memory_service.search_code_patterns(search_query, limit, language, min_success_rate)
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


@app.post("/optimize")
async def optimize_collections():
    """Optimize all collections for better performance"""
    try:
        await memory_service.optimize_collections()
        return {"status": "success", "message": "Collections optimized"}
    except Exception as e:
        logger.error(f"Error optimizing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/store/patterns")
async def batch_store_patterns(data: Dict[str, Any]):
    """Batch store multiple code patterns for efficiency"""
    try:
        patterns = data.get("patterns", [])
        if not patterns:
            raise HTTPException(status_code=400, detail="No patterns provided")
        
        if len(patterns) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 patterns per batch")
        
        result = await memory_service.batch_store_code_patterns(patterns)
        return {
            "status": "success",
            "summary": {
                "total": len(patterns),
                "successful": result["success"],
                "failed": result["failed"]
            },
            "ids": result["ids"],
            "errors": result["errors"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch store: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/search/patterns")
async def batch_search_patterns(data: Dict[str, Any]):
    """Batch search for multiple queries"""
    try:
        queries = data.get("queries", [])
        limit = data.get("limit", 5)
        
        if not queries:
            raise HTTPException(status_code=400, detail="No queries provided")
        
        if len(queries) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 queries per batch")
        
        results = await memory_service.batch_search_patterns(queries, limit)
        
        # Format response
        response = []
        for i, query in enumerate(queries):
            response.append({
                "query": query,
                "results": results[i] if i < len(results) else []
            })
        
        return {
            "status": "success",
            "batch_results": response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/update/metrics")
async def batch_update_metrics(data: Dict[str, Any]):
    """Batch update metrics for multiple patterns"""
    try:
        updates = data.get("updates", [])
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        if len(updates) > 500:
            raise HTTPException(status_code=400, detail="Maximum 500 updates per batch")
        
        result = await memory_service.batch_update_metrics(updates)
        
        return {
            "status": "success",
            "summary": {
                "total": len(updates),
                "successful": result["success"],
                "failed": result["failed"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/indexes")
async def get_indexes():
    """Get information about collection indexes"""
    try:
        index_info = {}
        
        for name, collection_name in COLLECTIONS.items():
            try:
                # Get collection info
                collection = memory_service.qdrant.get_collection(collection_name)
                
                # Note: Qdrant doesn't expose index details via API
                # This is a placeholder for index information
                index_info[name] = {
                    "collection": collection_name,
                    "points_count": collection.points_count,
                    "vectors_count": collection.vectors_count,
                    "status": "indexed" if collection.points_count > 0 else "empty",
                    "optimizer_status": collection.status,
                    "segments_count": collection.segments_count if hasattr(collection, 'segments_count') else "unknown"
                }
            except Exception as e:
                index_info[name] = {"error": str(e)}
        
        return {"status": "success", "indexes": index_info}
        
    except Exception as e:
        logger.error(f"Error getting index info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
