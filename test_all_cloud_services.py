#!/usr/bin/env python3
"""
Complete test of all cloud services
"""
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load cloud environment
load_dotenv('.env.cloud')

async def test_supabase():
    """Test Supabase PostgreSQL"""
    print("\n🔍 Testing Supabase...")
    try:
        import psycopg2
        
        db_url = os.getenv('SUPABASE_DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected! PostgreSQL {version[0]}")
        
        # Create tables if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_connection (
                id SERIAL PRIMARY KEY,
                test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message TEXT
            );
        """)
        
        # Insert test record
        cursor.execute(
            "INSERT INTO test_connection (message) VALUES (%s)",
            (f"Test from QLP at {datetime.now()}",)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Supabase test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return False

async def test_qdrant():
    """Test Qdrant Cloud"""
    print("\n🔍 Testing Qdrant Cloud...")
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            url=os.getenv('QDRANT_CLOUD_URL'),
            api_key=os.getenv('QDRANT_CLOUD_API_KEY')
        )
        
        # Get collections
        collections = client.get_collections()
        print(f"✅ Connected! Collections: {[c.name for c in collections.collections]}")
        
        # Create collection if needed
        collection_names = [col.name for col in collections.collections]
        if 'qlp_vectors' not in collection_names:
            print("Creating qlp_vectors collection...")
            client.create_collection(
                collection_name="qlp_vectors",
                vectors_config={
                    "size": 1536,
                    "distance": "Cosine"
                }
            )
            print("✅ Collection created!")
        
        # Test vector insertion
        from uuid import uuid4
        test_id = str(uuid4())
        client.upsert(
            collection_name="qlp_vectors",
            points=[{
                "id": test_id,
                "vector": [0.1] * 1536,
                "payload": {
                    "test": True,
                    "timestamp": datetime.now().isoformat()
                }
            }]
        )
        
        # Search test
        results = client.search(
            collection_name="qlp_vectors",
            query_vector=[0.1] * 1536,
            limit=1
        )
        
        print(f"✅ Qdrant test complete! Found {len(results)} results")
        return True
        
    except Exception as e:
        print(f"❌ Qdrant error: {e}")
        return False

async def test_temporal():
    """Test Temporal Cloud"""
    print("\n🔍 Testing Temporal Cloud...")
    try:
        from src.common.temporal_cloud import get_temporal_client
        
        # Test connection
        client = await get_temporal_client()
        
        # List workflows (should work even if empty)
        workflows = []
        async for workflow in client.list_workflows():
            workflows.append(workflow)
            if len(workflows) >= 5:  # Just get first 5
                break
        
        print(f"✅ Connected to Temporal Cloud!")
        print(f"   Namespace: {os.getenv('TEMPORAL_CLOUD_NAMESPACE')}")
        print(f"   Workflows found: {len(workflows)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Temporal error: {e}")
        print("   Note: If using API key auth, ensure TEMPORAL_CLOUD_API_KEY is set")
        return False

async def test_services_integration():
    """Test that services can work together"""
    print("\n🔍 Testing service integration...")
    
    # Test that we can create a record in Supabase and reference it in Qdrant
    try:
        import psycopg2
        from qdrant_client import QdrantClient
        from uuid import uuid4
        
        test_id = str(uuid4())
        
        # Create record in Supabase
        conn = psycopg2.connect(os.getenv('SUPABASE_DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qlp_test_integration (
                id UUID PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute(
            "INSERT INTO qlp_test_integration (id, name) VALUES (%s, %s)",
            (test_id, "Integration test")
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Reference in Qdrant
        client = QdrantClient(
            url=os.getenv('QDRANT_CLOUD_URL'),
            api_key=os.getenv('QDRANT_CLOUD_API_KEY')
        )
        
        client.upsert(
            collection_name="qlp_vectors",
            points=[{
                "id": test_id,
                "vector": [0.2] * 1536,
                "payload": {
                    "source": "supabase",
                    "table": "qlp_test_integration",
                    "test": True
                }
            }]
        )
        
        print(f"✅ Integration test complete! Test ID: {test_id}")
        return True
        
    except Exception as e:
        print(f"❌ Integration error: {e}")
        return False

async def main():
    print("🚀 Testing QLP Cloud Services")
    print("============================")
    
    results = {}
    
    # Test each service
    results['supabase'] = await test_supabase()
    results['qdrant'] = await test_qdrant()
    results['temporal'] = await test_temporal()
    results['integration'] = await test_services_integration()
    
    # Summary
    print("\n📊 Test Summary")
    print("===============")
    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{service.upper()}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All cloud services are working!")
        print("\nNext steps:")
        print("1. Copy .env to .env.backup")
        print("2. Copy .env.cloud to .env")
        print("3. docker-compose -f docker-compose.cloud-services.yml up -d")
    else:
        print("\n⚠️  Some services failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())