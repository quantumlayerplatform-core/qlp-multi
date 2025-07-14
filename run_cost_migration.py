#!/usr/bin/env python3
"""
Run cost tracking database migration
"""

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    # Try psycopg2-binary
    import psycopg2_binary as psycopg2
    from psycopg2_binary.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from pathlib import Path

# Database connection from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://qlp_user:secure_password123@localhost:5432/quantum_layer_db")

def run_migration():
    """Run the cost tracking migration"""
    
    # Read migration file
    migration_file = Path("migrations/003_create_cost_tracking_tables.sql")
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    migration_sql = migration_file.read_text()
    
    # Connect to database
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("🔗 Connected to database")
        
        # Run migration
        print("🚀 Running cost tracking migration...")
        cursor.execute(migration_sql)
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('llm_usage', 'cost_alerts')
        """)
        
        tables = cursor.fetchall()
        if len(tables) == 2:
            print("✅ Cost tracking tables created successfully!")
            
            # Check materialized views
            cursor.execute("""
                SELECT matviewname 
                FROM pg_matviews 
                WHERE schemaname = 'public' 
                AND matviewname IN ('daily_llm_costs', 'monthly_llm_costs')
            """)
            
            views = cursor.fetchall()
            if len(views) == 2:
                print("✅ Cost aggregation views created successfully!")
            else:
                print("⚠️ Some materialized views may not have been created")
        else:
            print("❌ Some tables were not created")
            return False
        
        # Show table structure
        print("\n📊 LLM Usage Table Structure:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'llm_usage'
            ORDER BY ordinal_position
        """)
        
        for col in cursor.fetchall():
            print(f"   - {col[0]}: {col[1]} {'(nullable)' if col[2] == 'YES' else ''}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
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