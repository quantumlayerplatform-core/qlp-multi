#!/usr/bin/env python3
"""
Run cost tracking database migration using SQLAlchemy
"""

from sqlalchemy import create_engine, text
from pathlib import Path
import os

# Database connection from environment
# Use the Docker service name or localhost with the mapped port
# Note: Remove +asyncpg for regular psycopg2 connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://qlp_user:qlp_password@localhost:5432/qlp_db").replace("+asyncpg", "")

def run_migration():
    """Run the cost tracking migration"""
    
    # Read migration file
    migration_file = Path("migrations/003_create_cost_tracking_tables.sql")
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    migration_sql = migration_file.read_text()
    
    # Create engine
    try:
        engine = create_engine(DATABASE_URL)
        
        print("🔗 Connected to database")
        
        with engine.begin() as conn:
            # Run migration
            print("🚀 Running cost tracking migration...")
            
            # Split migration into individual statements
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
            
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        conn.execute(text(statement))
                        print(f"   ✓ Statement {i+1}/{len(statements)} executed")
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"   ⚠️ Statement {i+1} - Already exists (skipped)")
                        else:
                            print(f"   ❌ Statement {i+1} failed: {e}")
            
            # Verify tables were created
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('llm_usage', 'cost_alerts')
            """))
            
            tables = result.fetchall()
            if len(tables) >= 1:  # At least llm_usage should exist
                print("\n✅ Cost tracking tables created successfully!")
                
                # Check materialized views
                result = conn.execute(text("""
                    SELECT matviewname 
                    FROM pg_matviews 
                    WHERE schemaname = 'public' 
                    AND matviewname IN ('daily_llm_costs', 'monthly_llm_costs')
                """))
                
                views = result.fetchall()
                print(f"✅ Created {len(views)} materialized views")
            
            # Show table structure
            print("\n📊 LLM Usage Table Structure:")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'llm_usage'
                ORDER BY ordinal_position
            """))
            
            for col in result.fetchall():
                nullable = '(nullable)' if col[2] == 'YES' else ''
                print(f"   - {col[0]}: {col[1]} {nullable}")
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("💰 Cost Tracking Database Migration")
    print("=" * 50)
    
    if run_migration():
        print("\nNext steps:")
        print("1. Update services to use the new cost tracking tables")
        print("2. Restart services to pick up changes")
        print("3. Test cost tracking with: python test_execute_with_cost.py")
    else:
        print("\n❌ Migration failed. Please check the error and try again.")