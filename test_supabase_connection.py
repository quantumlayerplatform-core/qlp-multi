#!/usr/bin/env python3
"""
Test Supabase connection from production environment
"""

import psycopg2
from urllib.parse import urlparse
import traceback

def test_connection():
    """Test direct connection to Supabase"""
    
    # Test URLs
    urls = [
        # Pooler connection (pgbouncer)
        "postgresql://postgres.piqrwahqrxuyfnzfoosq:nwGE5hunfncm57NU@aws-0-eu-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true",
        # Direct connection  
        "postgresql://postgres.piqrwahqrxuyfnzfoosq:nwGE5hunfncm57NU@aws-0-eu-west-2.pooler.supabase.com:5432/postgres",
        # Alternative format
        "postgresql://postgres:nwGE5hunfncm57NU@db.piqrwahqrxuyfnzfoosq.supabase.co:5432/postgres"
    ]
    
    for i, database_url in enumerate(urls):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: Testing connection...")
        print(f"URL: {database_url[:50]}...")
        
        try:
            # Parse URL
            result = urlparse(database_url)
            
            # Connect
            conn = psycopg2.connect(
                database=result.path[1:].split('?')[0],  # Remove leading / and query params
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            
            print("✅ Connected successfully!")
            
            # Test query
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"Database version: {version[:50]}...")
            
            # Check tables
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = 'capsules'
            """)
            
            if cur.fetchone():
                print("✅ 'capsules' table exists")
                
                # Count rows
                cur.execute("SELECT COUNT(*) FROM capsules")
                count = cur.fetchone()[0]
                print(f"Capsules count: {count}")
            else:
                print("❌ 'capsules' table NOT found")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    print("Testing Supabase connections...")
    test_connection()