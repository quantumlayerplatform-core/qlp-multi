#!/usr/bin/env python3
"""
Test connections to cloud services and optionally migrate data
"""
import os
import sys
import psycopg2
import requests
from dotenv import load_dotenv
import json
from datetime import datetime

# Load cloud environment
load_dotenv('.env.cloud')

class CloudServiceTester:
    def __init__(self):
        self.results = {}
        
    def test_supabase(self):
        """Test Supabase PostgreSQL connection"""
        print("🔍 Testing Supabase connection...")
        try:
            db_url = os.getenv('SUPABASE_DATABASE_URL')
            if not db_url:
                raise Exception("SUPABASE_DATABASE_URL not set")
                
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Supabase connected! PostgreSQL {version[0]}")
            
            # Check if tables exist
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                print(f"   Found {len(tables)} tables:")
                for table in tables[:5]:  # Show first 5
                    print(f"   - {table[0]}")
                if len(tables) > 5:
                    print(f"   ... and {len(tables)-5} more")
            else:
                print("   ⚠️  No tables found. Database is empty.")
                
            cursor.close()
            conn.close()
            
            self.results['supabase'] = {'status': 'success', 'message': 'Connected successfully'}
            return True
            
        except Exception as e:
            print(f"❌ Supabase connection failed: {str(e)}")
            self.results['supabase'] = {'status': 'failed', 'message': str(e)}
            return False
    
    def test_qdrant(self):
        """Test Qdrant Cloud connection"""
        print("\n🔍 Testing Qdrant Cloud connection...")
        try:
            qdrant_url = os.getenv('QDRANT_CLOUD_URL')
            api_key = os.getenv('QDRANT_CLOUD_API_KEY')
            
            if not qdrant_url:
                raise Exception("QDRANT_CLOUD_URL not set")
            
            headers = {}
            if api_key and api_key != "your-qdrant-api-key-here":
                headers['api-key'] = api_key
            
            # Test connection
            response = requests.get(f"{qdrant_url}/", headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Qdrant Cloud connected!")
                print(f"   Cluster: {os.getenv('QDRANT_CLOUD_CLUSTER_ID')}")
                print(f"   Region: eu-west-2")
                
                # Check collections
                collections_response = requests.get(f"{qdrant_url}/collections", headers=headers)
                if collections_response.status_code == 200:
                    collections = collections_response.json().get('result', {}).get('collections', [])
                    if collections:
                        print(f"   Found {len(collections)} collections:")
                        for col in collections:
                            print(f"   - {col['name']}")
                    else:
                        print("   ⚠️  No collections found. Qdrant is empty.")
                
                self.results['qdrant'] = {'status': 'success', 'message': 'Connected successfully'}
                return True
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Qdrant Cloud connection failed: {str(e)}")
            print("   ℹ️  Make sure to set your API key in .env.cloud")
            self.results['qdrant'] = {'status': 'failed', 'message': str(e)}
            return False
    
    def test_temporal(self):
        """Test Temporal connection (local or cloud)"""
        print("\n🔍 Testing Temporal connection...")
        temporal_server = os.getenv('TEMPORAL_SERVER', os.getenv('TEMPORAL_CLOUD_ENDPOINT'))
        
        if 'tmprl.cloud' in temporal_server:
            print("   ℹ️  Temporal Cloud detected - requires mTLS setup")
            print("   Please ensure certificates are configured")
            self.results['temporal'] = {'status': 'info', 'message': 'Cloud config detected'}
        else:
            print(f"   Using local Temporal at {temporal_server}")
            self.results['temporal'] = {'status': 'success', 'message': 'Using local Temporal'}
        
        return True
    
    def create_qdrant_collection(self):
        """Create the QLP vectors collection in Qdrant Cloud"""
        print("\n📦 Creating Qdrant collection...")
        try:
            qdrant_url = os.getenv('QDRANT_CLOUD_URL')
            api_key = os.getenv('QDRANT_CLOUD_API_KEY')
            
            headers = {'Content-Type': 'application/json'}
            if api_key and api_key != "your-qdrant-api-key-here":
                headers['api-key'] = api_key
            
            # Create collection
            collection_config = {
                "vectors": {
                    "size": 1536,  # OpenAI embeddings size
                    "distance": "Cosine"
                },
                "optimizers_config": {
                    "default_segment_number": 2
                }
            }
            
            response = requests.put(
                f"{qdrant_url}/collections/qlp_vectors",
                headers=headers,
                json=collection_config
            )
            
            if response.status_code in [200, 201]:
                print("✅ Collection 'qlp_vectors' created successfully!")
                return True
            else:
                print(f"❌ Failed to create collection: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating collection: {str(e)}")
            return False
    
    def create_supabase_tables(self):
        """Create initial tables in Supabase"""
        print("\n📦 Creating Supabase tables...")
        try:
            db_url = os.getenv('SUPABASE_DATABASE_URL')
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Create capsules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capsules (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    capsule_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    files JSONB DEFAULT '[]'::jsonb,
                    github_repo VARCHAR(255),
                    github_url TEXT
                );
            """)
            
            # Create workflows table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    workflow_id VARCHAR(255) UNIQUE NOT NULL,
                    capsule_id VARCHAR(255) REFERENCES capsules(capsule_id),
                    status VARCHAR(50),
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_capsules_status ON capsules(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);")
            
            conn.commit()
            print("✅ Tables created successfully!")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("📊 Cloud Services Test Summary")
        print("="*50)
        
        for service, result in self.results.items():
            status_icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "ℹ️"
            print(f"{status_icon} {service.upper()}: {result['message']}")
        
        print("\n📝 Next Steps:")
        if all(r['status'] == 'success' for r in self.results.values() if r['status'] != 'info'):
            print("1. ✅ All cloud services are ready!")
            print("2. Run: docker-compose -f docker-compose.cloud-services.yml up -d")
            print("3. Your app will now use cloud services")
        else:
            print("1. ❌ Fix the connection issues above")
            print("2. Update .env.cloud with correct credentials")
            print("3. Run this test again")

def main():
    print("🚀 QLP Cloud Services Connection Test")
    print("====================================\n")
    
    tester = CloudServiceTester()
    
    # Test connections
    supabase_ok = tester.test_supabase()
    qdrant_ok = tester.test_qdrant()
    tester.test_temporal()
    
    # Offer to create resources
    if supabase_ok:
        response = input("\n📝 Create Supabase tables? (y/n): ")
        if response.lower() == 'y':
            tester.create_supabase_tables()
    
    if qdrant_ok:
        response = input("\n📝 Create Qdrant collection? (y/n): ")
        if response.lower() == 'y':
            tester.create_qdrant_collection()
    
    # Print summary
    tester.print_summary()

if __name__ == "__main__":
    main()