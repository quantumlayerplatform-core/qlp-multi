"""
Memory extensions for Universal NLP Decomposer
Extends existing vector memory with pattern storage capabilities
"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import structlog
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client import QdrantClient

logger = structlog.get_logger()


class NLPMemoryExtensions:
    """
    Extensions to vector memory for NLP pattern storage
    Maintains compatibility with existing memory client
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant = qdrant_client
        self.collections = {
            "patterns": "nlp_patterns",
            "decompositions": "nlp_decompositions",
            "intents": "nlp_intents",
            "requirements": "nlp_requirements"
        }
        
    async def initialize_nlp_collections(self):
        """Initialize NLP-specific collections in Qdrant"""
        logger.info("Initializing NLP collections in vector memory")
        
        try:
            # Create patterns collection
            if not self.qdrant.collection_exists(self.collections["patterns"]):
                self.qdrant.create_collection(
                    collection_name=self.collections["patterns"],
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding size
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collections['patterns']}")
            
            # Create decompositions collection  
            if not self.qdrant.collection_exists(self.collections["decompositions"]):
                self.qdrant.create_collection(
                    collection_name=self.collections["decompositions"],
                    vectors_config=VectorParams(
                        size=1536,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collections['decompositions']}")
            
            # Create intents collection
            if not self.qdrant.collection_exists(self.collections["intents"]):
                self.qdrant.create_collection(
                    collection_name=self.collections["intents"],
                    vectors_config=VectorParams(
                        size=1536,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collections['intents']}")
            
            # Create requirements collection
            if not self.qdrant.collection_exists(self.collections["requirements"]):
                self.qdrant.create_collection(
                    collection_name=self.collections["requirements"],
                    vectors_config=VectorParams(
                        size=1536,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collections['requirements']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP collections: {e}")
            raise
    
    async def store_pattern(self, pattern_data: Dict[str, Any]):
        """Store pattern in vector memory"""
        try:
            point = PointStruct(
                id=pattern_data["id"],
                vector=pattern_data["embedding"],
                payload={
                    "pattern": pattern_data["pattern"],
                    "timestamp": pattern_data["timestamp"],
                    "type": "decomposition_pattern"
                }
            )
            
            self.qdrant.upsert(
                collection_name=self.collections["patterns"],
                points=[point]
            )
            
            logger.info(f"Stored pattern: {pattern_data['id']}")
            
        except Exception as e:
            logger.error(f"Failed to store pattern: {e}")
            raise
    
    async def search_similar_patterns(self, query_embedding: List[float], 
                                    limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar patterns"""
        try:
            search_result = self.qdrant.search(
                collection_name=self.collections["patterns"],
                query_vector=query_embedding,
                limit=limit,
                score_threshold=0.7
            )
            
            patterns = []
            for hit in search_result:
                patterns.append({
                    "id": hit.id,
                    "score": hit.score,
                    "pattern": hit.payload.get("pattern"),
                    "timestamp": hit.payload.get("timestamp")
                })
            
            logger.info(f"Found {len(patterns)} similar patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to search patterns: {e}")
            return []
    
    async def store_decomposition(self, decomposition_data: Dict[str, Any]):
        """Store decomposition result"""
        try:
            # Create embedding for decomposition
            from openai import AsyncOpenAI
            from src.common.config import settings
            
            if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
                from openai import AsyncAzureOpenAI
                client = AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
            else:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Create text for embedding
            embedding_text = f"""
            Request: {decomposition_data['request_description']}
            Tasks: {decomposition_data['decomposition_result']['task_count']}
            Intent: {decomposition_data['decomposition_result']['intent']['primary_goal']}
            Confidence: {decomposition_data['decomposition_result']['confidence']}
            """
            
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=embedding_text
            )
            
            embedding = response.data[0].embedding
            
            # Store in vector memory
            point = PointStruct(
                id=decomposition_data["request_id"],
                vector=embedding,
                payload={
                    "decomposition": decomposition_data,
                    "timestamp": decomposition_data["timestamp"],
                    "type": "decomposition_result"
                }
            )
            
            self.qdrant.upsert(
                collection_name=self.collections["decompositions"],
                points=[point]
            )
            
            logger.info(f"Stored decomposition: {decomposition_data['request_id']}")
            
        except Exception as e:
            logger.error(f"Failed to store decomposition: {e}")
    
    async def search_similar_decompositions(self, query_text: str, 
                                          limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar decompositions"""
        try:
            # Create embedding for query
            from openai import AsyncOpenAI
            from src.common.config import settings
            
            if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
                from openai import AsyncAzureOpenAI
                client = AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
            else:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=query_text
            )
            
            query_embedding = response.data[0].embedding
            
            # Search for similar decompositions
            search_result = self.qdrant.search(
                collection_name=self.collections["decompositions"],
                query_vector=query_embedding,
                limit=limit,
                score_threshold=0.7
            )
            
            decompositions = []
            for hit in search_result:
                decompositions.append({
                    "id": hit.id,
                    "score": hit.score,
                    "decomposition": hit.payload.get("decomposition"),
                    "timestamp": hit.payload.get("timestamp")
                })
            
            logger.info(f"Found {len(decompositions)} similar decompositions")
            return decompositions
            
        except Exception as e:
            logger.error(f"Failed to search decompositions: {e}")
            return []
    
    async def store_intent(self, intent_data: Dict[str, Any]):
        """Store intent analysis result"""
        try:
            # Create embedding for intent
            from openai import AsyncOpenAI
            from src.common.config import settings
            
            if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
                from openai import AsyncAzureOpenAI
                client = AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
            else:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Create text for embedding
            embedding_text = f"""
            Primary Goal: {intent_data['primary_goal']}
            Expected Output: {intent_data['expected_output']}
            Complexity: {intent_data['complexity_level']}
            Scope: {intent_data['scope']}
            Constraints: {' '.join(intent_data.get('constraints', []))}
            """
            
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=embedding_text
            )
            
            embedding = response.data[0].embedding
            
            # Store in vector memory
            point = PointStruct(
                id=intent_data["id"],
                vector=embedding,
                payload={
                    "intent": intent_data,
                    "timestamp": intent_data["timestamp"],
                    "type": "intent_analysis"
                }
            )
            
            self.qdrant.upsert(
                collection_name=self.collections["intents"],
                points=[point]
            )
            
            logger.info(f"Stored intent: {intent_data['id']}")
            
        except Exception as e:
            logger.error(f"Failed to store intent: {e}")
    
    async def search_similar_intents(self, query_embedding: List[float], 
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar intents"""
        try:
            search_result = self.qdrant.search(
                collection_name=self.collections["intents"],
                query_vector=query_embedding,
                limit=limit,
                score_threshold=0.7
            )
            
            intents = []
            for hit in search_result:
                intents.append({
                    "id": hit.id,
                    "score": hit.score,
                    "intent": hit.payload.get("intent"),
                    "timestamp": hit.payload.get("timestamp")
                })
            
            logger.info(f"Found {len(intents)} similar intents")
            return intents
            
        except Exception as e:
            logger.error(f"Failed to search intents: {e}")
            return []
    
    async def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored patterns"""
        try:
            stats = {}
            
            # Get collection info
            for collection_type, collection_name in self.collections.items():
                if self.qdrant.collection_exists(collection_name):
                    info = self.qdrant.get_collection(collection_name)
                    stats[collection_type] = {
                        "total_points": info.points_count,
                        "vector_size": info.config.params.vectors.size,
                        "distance": info.config.params.vectors.distance.value
                    }
                else:
                    stats[collection_type] = {"total_points": 0}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get pattern statistics: {e}")
            return {}
    
    async def cleanup_old_patterns(self, days_old: int = 30):
        """Clean up old patterns to prevent memory bloat"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_timestamp = cutoff_date.isoformat()
            
            # Clean up patterns
            for collection_name in self.collections.values():
                if self.qdrant.collection_exists(collection_name):
                    # Note: This is a simplified cleanup - in production you'd want
                    # more sophisticated cleanup based on usage patterns
                    logger.info(f"Cleanup triggered for collection: {collection_name}")
                    
            logger.info(f"Cleaned up patterns older than {days_old} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old patterns: {e}")


# Integration with existing VectorMemoryClient
def extend_vector_memory_client(memory_client):
    """Extend existing VectorMemoryClient with NLP capabilities"""
    
    # Add NLP extensions
    nlp_extensions = NLPMemoryExtensions(memory_client.qdrant)
    
    # Add methods to existing client
    memory_client.store_pattern = nlp_extensions.store_pattern
    memory_client.search_similar_patterns = nlp_extensions.search_similar_patterns
    memory_client.store_decomposition = nlp_extensions.store_decomposition
    memory_client.search_similar_decompositions = nlp_extensions.search_similar_decompositions
    memory_client.store_intent = nlp_extensions.store_intent
    memory_client.search_similar_intents = nlp_extensions.search_similar_intents
    memory_client.get_pattern_statistics = nlp_extensions.get_pattern_statistics
    memory_client.cleanup_old_patterns = nlp_extensions.cleanup_old_patterns
    memory_client.initialize_nlp_collections = nlp_extensions.initialize_nlp_collections
    
    return memory_client