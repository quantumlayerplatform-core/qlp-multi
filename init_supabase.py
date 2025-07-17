#!/usr/bin/env python3
"""
Initialize Supabase Database Tables for QLP Production
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

def get_supabase_connection():
    """Get connection to Supabase database"""
    # Get DATABASE_URL from environment or use the production URL
    database_url = os.getenv("DATABASE_URL", 
        "postgresql://postgres.piqrwahqrxuyfnzfoosq:nwGE5hunfncm57NU@aws-0-eu-west-2.pooler.supabase.com:5432/postgres")
    
    # Parse the URL
    result = urlparse(database_url)
    
    connection = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    
    return connection

def init_supabase_tables():
    """Initialize all required tables in Supabase"""
    try:
        conn = get_supabase_connection()
        cur = conn.cursor()
        
        print("🔌 Connected to Supabase database")
        
        # SQL commands to create tables
        sql_commands = """
-- Create capsules table
CREATE TABLE IF NOT EXISTS capsules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    manifest JSONB DEFAULT '{}',
    source_code JSONB DEFAULT '{}',
    tests JSONB DEFAULT '{}',
    documentation TEXT DEFAULT '',
    validation_report JSONB,
    deployment_config JSONB DEFAULT '{}',
    confidence_score FLOAT DEFAULT 0.0,
    execution_duration FLOAT DEFAULT 0.0,
    file_count INTEGER DEFAULT 0,
    total_size_bytes INTEGER DEFAULT 0,
    meta_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'created',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_capsule_request ON capsules(request_id);
CREATE INDEX IF NOT EXISTS idx_capsule_tenant_user ON capsules(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_capsule_created ON capsules(created_at);
CREATE INDEX IF NOT EXISTS idx_capsule_status ON capsules(status);

-- Create versions table
CREATE TABLE IF NOT EXISTS capsule_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    version_number VARCHAR(50) NOT NULL,
    parent_version_id UUID,
    author VARCHAR(255) NOT NULL,
    message TEXT,
    changes JSONB DEFAULT '{}',
    branch VARCHAR(100) DEFAULT 'main',
    tags JSONB DEFAULT '[]',
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_version_capsule ON capsule_versions(capsule_id);
CREATE INDEX IF NOT EXISTS idx_version_created ON capsule_versions(created_at);

-- Create deliveries table
CREATE TABLE IF NOT EXISTS capsule_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    version_id UUID REFERENCES capsule_versions(id),
    provider VARCHAR(50) NOT NULL,
    destination VARCHAR(500) NOT NULL,
    delivery_config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    url TEXT,
    signed_url TEXT,
    checksum VARCHAR(64),
    meta_data JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_delivery_capsule ON capsule_deliveries(capsule_id);
CREATE INDEX IF NOT EXISTS idx_delivery_status ON capsule_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_delivery_created ON capsule_deliveries(created_at);

-- Create signatures table
CREATE TABLE IF NOT EXISTS capsule_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    version_id UUID REFERENCES capsule_versions(id),
    signature TEXT NOT NULL,
    algorithm VARCHAR(50) DEFAULT 'HMAC-SHA256',
    signer VARCHAR(255),
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_signature_capsule ON capsule_signatures(capsule_id);

-- Create workflow checkpoints table (for Temporal workflows)
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL UNIQUE,
    request_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    checkpoint_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'running',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_checkpoint_workflow ON workflow_checkpoints(workflow_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_request ON workflow_checkpoints(request_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_status ON workflow_checkpoints(status);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_capsules_updated_at ON capsules;
CREATE TRIGGER update_capsules_updated_at 
    BEFORE UPDATE ON capsules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_workflow_checkpoints_updated_at ON workflow_checkpoints;
CREATE TRIGGER update_workflow_checkpoints_updated_at 
    BEFORE UPDATE ON workflow_checkpoints 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
"""
        
        print("📝 Creating tables...")
        cur.execute(sql_commands)
        conn.commit()
        
        # Verify tables were created
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('capsules', 'capsule_versions', 'capsule_deliveries', 'capsule_signatures', 'workflow_checkpoints')
            ORDER BY tablename;
        """)
        
        tables = cur.fetchall()
        print("\n✅ Successfully created/verified tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check if tables have any data
        print("\n📊 Table statistics:")
        for table in ['capsules', 'capsule_versions', 'capsule_deliveries', 'capsule_signatures', 'workflow_checkpoints']:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  - {table}: {count} rows")
        
        cur.close()
        conn.close()
        
        print("\n✅ Supabase database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error initializing Supabase: {str(e)}")
        return False

def test_capsule_insert():
    """Test inserting a capsule to verify database is working"""
    try:
        conn = get_supabase_connection()
        cur = conn.cursor()
        
        print("\n🧪 Testing capsule insertion...")
        
        # Insert a test capsule
        cur.execute("""
            INSERT INTO capsules (
                request_id, tenant_id, user_id, 
                manifest, source_code, status
            ) VALUES (
                'test-request-001', 'test-tenant', 'test-user',
                '{"name": "test-capsule", "version": "1.0.0"}',
                '{"main.py": "print(\"Hello from test capsule\")"}',
                'completed'
            ) RETURNING id;
        """)
        
        capsule_id = cur.fetchone()[0]
        conn.commit()
        
        print(f"✅ Test capsule created with ID: {capsule_id}")
        
        # Clean up test data
        cur.execute("DELETE FROM capsules WHERE request_id = 'test-request-001'")
        conn.commit()
        print("🧹 Test data cleaned up")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Initializing Supabase Database for QLP Production")
    print("=" * 60)
    
    # Initialize tables
    if init_supabase_tables():
        # Test insertion
        test_capsule_insert()
        print("\n✅ Supabase is ready for capsule storage!")
    else:
        print("\n❌ Failed to initialize Supabase")
        sys.exit(1)