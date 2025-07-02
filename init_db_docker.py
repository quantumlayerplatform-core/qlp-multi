#!/usr/bin/env python3
"""
Initialize Database via Docker exec
"""

import subprocess
import sys

def init_database():
    """Initialize database tables using Docker exec"""
    try:
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

-- List all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
"""
        
        # Execute SQL via Docker
        cmd = [
            "docker", "exec", "-i", "qlp-postgres",
            "psql", "-U", "qlp_user", "-d", "qlp_db"
        ]
        
        print("Initializing database tables...")
        result = subprocess.run(
            cmd,
            input=sql_commands,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Database initialized successfully!")
            print("\nCreated tables:")
            # Parse output to show tables
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('-') and 'tablename' not in line and 'row' not in line:
                    print(f"  - {line.strip()}")
            return True
        else:
            print(f"❌ Database initialization failed!")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)