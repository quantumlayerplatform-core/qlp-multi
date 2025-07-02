#!/usr/bin/env python3
"""
Initialize QLP Database
Production database initialization script
"""

import sys
import os
sys.path.append('.')

from src.common.database import db_manager
from src.common.logger import get_logger

logger = get_logger(__name__)


def init_database():
    """Initialize the database with all required tables"""
    try:
        logger.info("Starting database initialization...")
        
        # Create all tables
        db_manager.create_tables()
        logger.info("Database tables created successfully")
        
        # Verify tables exist
        with db_manager.session_scope() as session:
            # Test connection
            result = session.execute("SELECT 1")
            logger.info("Database connection verified")
            
            # Check tables
            tables = session.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """).fetchall()
            
            logger.info(f"Created tables: {[t[0] for t in tables]}")
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Make sure we have the right environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Use the docker-compose PostgreSQL settings
        os.environ['DATABASE_URL'] = 'postgresql://qlp_user:qlp_password@localhost:5432/qlp_db'
    
    success = init_database()
    sys.exit(0 if success else 1)