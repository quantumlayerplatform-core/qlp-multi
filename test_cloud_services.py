#!/usr/bin/env python3
"""
Quick test of cloud services connections
"""
import os
from dotenv import load_dotenv

# Load cloud environment
load_dotenv('.env.cloud')

def test_qdrant():
    """Test Qdrant Cloud connection"""
    print("Testing Qdrant Cloud...")
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            url=os.getenv('QDRANT_CLOUD_URL'),
            api_key=os.getenv('QDRANT_CLOUD_API_KEY')
        )
        
        # Get collections
        collections = client.get_collections()
        print(f"✅ Qdrant connected! Collections: {collections}")
        
        # Create qlp_vectors collection if it doesn't exist
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
        else:
            print("✅ qlp_vectors collection already exists")
            
    except Exception as e:
        print(f"❌ Qdrant error: {e}")

def test_supabase():
    """Test Supabase connection"""
    print("\nTesting Supabase...")
    try:
        import psycopg2
        
        conn = psycopg2.connect(os.getenv('SUPABASE_DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Supabase connected! PostgreSQL: {version[0]}")
        
        # Check tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Tables: {tables if tables else 'No tables yet'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Supabase error: {e}")

def main():
    print("🚀 Testing Cloud Services\n")
    test_qdrant()
    test_supabase()
    
    print("\n✅ Ready to switch to cloud services!")
    print("Run: docker-compose -f docker-compose.cloud-services.yml up -d")

if __name__ == "__main__":
    main()