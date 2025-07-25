#!/usr/bin/env python3
"""
Database Initialization Script
Creates all necessary tables and indexes for QLP production deployment
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.database import db_manager, Base
from src.common.config import settings
import structlog

logger = structlog.get_logger()


def create_database_schema():
    """Create all database tables and indexes"""
    try:
        logger.info("Creating database schema...")
        
        # Create all tables
        db_manager.create_tables()
        
        logger.info(
            "Database schema created successfully",
            database_url=db_manager.database_url.replace(settings.POSTGRES_PASSWORD, "***")
        )
        
        # Verify tables were created
        with db_manager.get_session() as session:
            # Test basic connection
            result = session.execute("SELECT 1").scalar()
            assert result == 1
            
            # Verify core tables exist
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """
            
            tables = session.execute(tables_query).fetchall()
            table_names = [table[0] for table in tables]
            
            required_tables = [
                'capsules',
                'capsule_versions', 
                'capsule_deliveries',
                'capsule_signatures'
            ]
            
            missing_tables = [t for t in required_tables if t not in table_names]
            
            if missing_tables:
                logger.error("Missing required tables", missing=missing_tables)
                return False
            
            logger.info(
                "Database schema verification completed",
                tables_created=len(table_names),
                table_names=table_names
            )
            
        return True
        
    except Exception as e:
        logger.error("Failed to create database schema", error=str(e))
        return False


def create_sample_data():
    """Create sample data for development/testing"""
    try:
        from src.common.database import CapsuleRepository
        from uuid import uuid4
        from datetime import datetime, timezone
        
        logger.info("Creating sample data...")
        
        with db_manager.get_session() as session:
            repository = CapsuleRepository(session)
            
            # Create sample capsule
            sample_capsule_data = {
                'id': str(uuid4()),
                'request_id': 'sample-request-001',
                'tenant_id': 'sample-tenant',
                'user_id': 'sample-user',
                'manifest': {
                    'name': 'Sample Python Application',
                    'description': 'A sample FastAPI application',
                    'language': 'python',
                    'framework': 'fastapi'
                },
                'source_code': {
                    'main.py': '''#!/usr/bin/env python3
"""
Sample FastAPI Application
Generated by Quantum Layer Platform
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Sample App", version="1.0.0")

class HealthResponse(BaseModel):
    status: str
    message: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy", 
        message="Sample application is running"
    )

@app.get("/")
async def root():
    return {"message": "Hello from QLP Sample App"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
                    'requirements.txt': '''fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
''',
                    'Dockerfile': '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
'''
                },
                'tests': {
                    'test_main.py': '''import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
'''
                },
                'documentation': '''# Sample FastAPI Application

This is a sample application generated by the Quantum Layer Platform.

## Features

- FastAPI web framework
- Health check endpoint
- Production-ready Docker container
- Comprehensive tests

## Running the Application

### Local Development
```bash
pip install -r requirements.txt
python main.py
```

### Docker
```bash
docker build -t sample-app .
docker run -p 8000:8000 sample-app
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## Testing

```bash
pytest test_main.py
```

Generated by QLP on ''' + datetime.now(timezone.utc).isoformat(),
                'confidence_score': 0.95,
                'execution_duration': 2.5,
                'file_count': 4,
                'total_size_bytes': 1024,
                'metadata': {
                    'languages': ['python'],
                    'frameworks': ['fastapi'],
                    'generated_by': 'qlp-sample-generator',
                    'sample_data': True
                },
                'status': 'stored'
            }
            
            capsule = repository.create_capsule(sample_capsule_data)
            
            # Create sample version
            version_data = {
                'capsule_id': capsule.id,
                'version_number': 1,
                'version_hash': 'abc123def456',
                'author': 'QLP System',
                'message': 'Initial version',
                'branch': 'main',
                'changes': [
                    {'path': 'main.py', 'type': 'added', 'size': 500},
                    {'path': 'requirements.txt', 'type': 'added', 'size': 50},
                    {'path': 'Dockerfile', 'type': 'added', 'size': 150},
                    {'path': 'test_main.py', 'type': 'added', 'size': 300}
                ],
                'files_added': 4,
                'files_modified': 0,
                'files_deleted': 0,
                'tags': ['v1.0.0', 'initial'],
                'is_release': True
            }
            
            version = repository.create_version(version_data)
            
            logger.info(
                "Sample data created successfully",
                capsule_id=str(capsule.id),
                version_id=str(version.id)
            )
            
        return True
        
    except Exception as e:
        logger.error("Failed to create sample data", error=str(e))
        return False


def main():
    """Main initialization function"""
    logger.info("Starting QLP database initialization...")
    
    # Check database connection
    try:
        with db_manager.get_session() as session:
            session.execute("SELECT 1")
        logger.info("Database connection successful")
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        sys.exit(1)
    
    # Create schema
    if not create_database_schema():
        logger.error("Schema creation failed")
        sys.exit(1)
    
    # Create sample data (optional)
    if len(sys.argv) > 1 and sys.argv[1] == "--with-sample-data":
        if not create_sample_data():
            logger.warning("Sample data creation failed, but schema is ready")
    
    logger.info("QLP database initialization completed successfully!")


if __name__ == "__main__":
    main()