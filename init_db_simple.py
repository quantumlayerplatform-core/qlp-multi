#!/usr/bin/env python3
"""Simple database initialization script"""

import os
import sys
from sqlalchemy import create_engine

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.common.database import Base

def init_database():
    """Initialize database tables"""
    # Get database URL
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://qlp_user:qlp_password@postgres:5432/qlp_db"
    )
    
    print(f"Connecting to database: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        print("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)