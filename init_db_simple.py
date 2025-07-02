#!/usr/bin/env python3
"""
Simple Database Initialization Script
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Set database URL
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://qlp_user:qlp_password@127.0.0.1:5432/qlp_db')

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Import the Base from database module to get all models
import sys
sys.path.append('.')

# Import to register all models
from src.common.database import Base, CapsuleModel, CapsuleVersionModel, CapsuleDeliveryModel, CapsuleSignatureModel

def init_database():
    """Initialize database tables"""
    try:
        print(f"Connecting to database: {DATABASE_URL}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully!")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in result]
            print(f"✅ Created tables: {tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)