#!/usr/bin/env python3
"""
Test Qdrant Payload Indexing Performance

This script tests the performance improvements from adding payload indexes
to Qdrant collections. It measures search speed with and without filters.
"""

import asyncio
import sys
import time
import uuid
from typing import List, Dict, Any
import random

# Add src to path for imports
sys.path.insert(0, '.')

from src.memory.main import memory_service, COLLECTIONS
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
import structlog

logger = structlog.get_logger()


async def generate_test_data(count: int = 1000) -> List[PointStruct]:
    """Generate test data for code patterns collection"""
    languages = ["python", "javascript", "go", "java", "rust"]
    success_rates = [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
    
    points = []
    for i in range(count):
        # Generate sample code text
        code_text = f"""
def function_{i}(param_{i}):
    '''Function that processes {i}'''
    result = param_{i} * {i}
    return result
"""
        
        # Get embedding
        embedding = await memory_service.get_embedding(code_text)
        
        # Create point with payload
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "description": f"Function that processes {i}",
                "code": code_text,
                "language": random.choice(languages),
                "capsule_id": f"capsule_{i // 10}",
                "request_id": f"request_{i // 5}",
                "validation_score": random.choice(success_rates),
                "created_at": f"2025-01-{(i % 30) + 1:02d}T12:00:00Z",
                "usage_count": random.randint(0, 100),
                "success_rate": random.choice(success_rates)
            }
        )
        points.append(point)
        
        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{count} test points...")
    
    return points


async def test_search_without_filters(query_text: str, limit: int = 10):
    """Test search performance without filters"""
    print(f"\n1. Testing search WITHOUT filters (limit={limit})")
    print("=" * 50)
    
    start_time = time.time()
    results = await memory_service.search_code_patterns(query_text, limit=limit)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} results in {elapsed:.3f}s")
    if results:
        print(f"  Top result: {results[0]['description'][:50]}...")
        print(f"  Score: {results[0]['score']:.3f}")
    
    return elapsed


async def test_search_with_language_filter(query_text: str, language: str, limit: int = 10):
    """Test search performance with language filter"""
    print(f"\n2. Testing search WITH language filter (language={language}, limit={limit})")
    print("=" * 50)
    
    start_time = time.time()
    results = await memory_service.search_code_patterns(
        query_text, 
        limit=limit,
        language=language
    )
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} results in {elapsed:.3f}s")
    if results:
        print(f"  Top result: {results[0]['description'][:50]}...")
        print(f"  Language: {results[0]['language']}")
        print(f"  Score: {results[0]['score']:.3f}")
    
    return elapsed


async def test_search_with_quality_filter(query_text: str, min_success_rate: float, limit: int = 10):
    """Test search performance with quality filter"""
    print(f"\n3. Testing search WITH quality filter (min_success_rate={min_success_rate}, limit={limit})")
    print("=" * 50)
    
    start_time = time.time()
    results = await memory_service.search_code_patterns(
        query_text, 
        limit=limit,
        min_success_rate=min_success_rate
    )
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} results in {elapsed:.3f}s")
    if results:
        print(f"  Top result: {results[0]['description'][:50]}...")
        print(f"  Success rate: {results[0]['success_rate']}")
        print(f"  Score: {results[0]['score']:.3f}")
    
    return elapsed


async def test_search_with_multiple_filters(query_text: str, language: str, min_success_rate: float, limit: int = 10):
    """Test search performance with multiple filters"""
    print(f"\n4. Testing search WITH multiple filters (language={language}, min_success_rate={min_success_rate}, limit={limit})")
    print("=" * 50)
    
    start_time = time.time()
    results = await memory_service.search_code_patterns(
        query_text, 
        limit=limit,
        language=language,
        min_success_rate=min_success_rate
    )
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} results in {elapsed:.3f}s")
    if results:
        print(f"  Top result: {results[0]['description'][:50]}...")
        print(f"  Language: {results[0]['language']}")
        print(f"  Success rate: {results[0]['success_rate']}")
        print(f"  Score: {results[0]['score']:.3f}")
    
    return elapsed


async def test_request_search_with_filters():
    """Test request search with tenant/user filters"""
    print(f"\n5. Testing request search WITH tenant/user filters")
    print("=" * 50)
    
    query = "process data and generate report"
    filters = {
        "tenant_id": "tenant_123",
        "user_id": "user_456"
    }
    
    start_time = time.time()
    results = await memory_service.search_similar_requests(
        query,
        limit=5,
        filters=filters
    )
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} results in {elapsed:.3f}s")
    if results:
        print(f"  Top result: {results[0]['description'][:50]}...")
        print(f"  Score: {results[0]['score']:.3f}")
    
    return elapsed


async def load_test_data():
    """Load test data into Qdrant if collection is empty"""
    collection_name = COLLECTIONS["code_patterns"]
    
    try:
        # Check if collection has data
        collection_info = memory_service.qdrant.get_collection(collection_name)
        
        if collection_info.points_count < 100:
            print(f"\nCollection has {collection_info.points_count} points. Loading test data...")
            
            # Generate and insert test data
            test_points = await generate_test_data(1000)
            
            # Insert in batches
            batch_size = 100
            for i in range(0, len(test_points), batch_size):
                batch = test_points[i:i + batch_size]
                memory_service.qdrant.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                print(f"Inserted batch {i // batch_size + 1}/{len(test_points) // batch_size}")
            
            print(f"✓ Loaded {len(test_points)} test points")
        else:
            print(f"\n✓ Collection already has {collection_info.points_count} points")
            
    except Exception as e:
        logger.error(f"Error loading test data: {e}")


async def main():
    """Run all tests"""
    print("Qdrant Payload Indexing Test Suite")
    print("==================================")
    
    # Initialize collections
    print("\nInitializing collections with payload indexes...")
    await memory_service.initialize_collections()
    
    # Load test data if needed
    await load_test_data()
    
    # Wait a bit for indexes to build
    print("\nWaiting for indexes to build...")
    await asyncio.sleep(2)
    
    # Test query
    query_text = "function that processes data"
    
    # Run tests
    times = {}
    
    times['no_filter'] = await test_search_without_filters(query_text)
    times['language_filter'] = await test_search_with_language_filter(query_text, "python")
    times['quality_filter'] = await test_search_with_quality_filter(query_text, 0.8)
    times['multiple_filters'] = await test_search_with_multiple_filters(query_text, "python", 0.8)
    times['request_filters'] = await test_request_search_with_filters()
    
    # Performance summary
    print("\n\nPerformance Summary")
    print("=" * 50)
    
    baseline = times['no_filter']
    for test_name, elapsed in times.items():
        if test_name == 'no_filter':
            print(f"{test_name:20}: {elapsed:.3f}s (baseline)")
        else:
            speedup = baseline / elapsed if elapsed > 0 else 0
            print(f"{test_name:20}: {elapsed:.3f}s ({speedup:.1f}x speedup)")
    
    # Show expected improvements
    print("\n\nExpected Improvements with Payload Indexing:")
    print("=" * 50)
    print("✓ Language filtering: 2-3x faster")
    print("✓ Quality filtering: 3-5x faster")
    print("✓ Multiple filters: 4-6x faster")
    print("✓ Tenant/user filtering: 5-10x faster")
    print("\nNote: Actual speedup depends on data distribution and query patterns")
    
    # Test collection stats
    print("\n\nCollection Statistics")
    print("=" * 50)
    
    for name, collection_name in COLLECTIONS.items():
        try:
            info = memory_service.qdrant.get_collection(collection_name)
            print(f"{name:20}: {info.points_count} points, {info.vectors_count} vectors")
        except:
            print(f"{name:20}: Not initialized")


if __name__ == "__main__":
    asyncio.run(main())