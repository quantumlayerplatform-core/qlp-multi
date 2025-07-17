#!/bin/bash
set -e

# Migration script to cloud services
# Helps migrate from local Docker services to managed cloud services

echo "🚀 QLP Cloud Services Migration Tool"
echo "===================================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}▶${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if .env.cloud exists
check_cloud_env() {
    if [ ! -f ".env.cloud" ]; then
        print_warning "Creating .env.cloud template..."
        cat > .env.cloud << 'EOF'
# Cloud Services Configuration
# Copy your existing .env values and add these:

# Supabase (PostgreSQL)
SUPABASE_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Qdrant Cloud
QDRANT_CLOUD_URL=https://[your-cluster].qdrant.io
QDRANT_CLOUD_API_KEY=your-api-key

# Temporal Cloud
TEMPORAL_CLOUD_ENDPOINT=[namespace].tmprl.cloud:7233
TEMPORAL_CLOUD_NAMESPACE=your-namespace
TEMPORAL_CLOUD_TLS_CERT=base64-encoded-cert
TEMPORAL_CLOUD_TLS_KEY=base64-encoded-key

# Optional: Redis Cloud
# REDIS_CLOUD_URL=redis://default:[password]@[endpoint]:[port]

# Copy all other variables from your .env file below:
EOF
        print_info "Please edit .env.cloud with your cloud service credentials"
        exit 1
    fi
}

# Backup local data
backup_data() {
    print_status "Backing up local data..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # Backup PostgreSQL
    if docker ps | grep -q qlp-postgres; then
        print_info "Backing up PostgreSQL..."
        docker exec qlp-postgres pg_dump -U qlp_user qlp_db > $BACKUP_DIR/postgres_backup.sql
        print_status "PostgreSQL backup saved to $BACKUP_DIR/postgres_backup.sql"
    fi
    
    # Backup Qdrant
    if docker ps | grep -q qlp-qdrant; then
        print_info "Creating Qdrant snapshot..."
        curl -X POST http://localhost:6333/collections/qlp_vectors/snapshots
        
        # Get latest snapshot name
        SNAPSHOT=$(curl -s http://localhost:6333/collections/qlp_vectors/snapshots | jq -r '.result[0].name')
        if [ ! -z "$SNAPSHOT" ]; then
            curl -s http://localhost:6333/collections/qlp_vectors/snapshots/$SNAPSHOT -o $BACKUP_DIR/qdrant_snapshot.tar
            print_status "Qdrant snapshot saved to $BACKUP_DIR/qdrant_snapshot.tar"
        fi
    fi
    
    # Backup Redis
    if docker ps | grep -q qlp-redis; then
        print_info "Backing up Redis..."
        docker exec qlp-redis redis-cli BGSAVE
        sleep 2
        docker cp qlp-redis:/data/dump.rdb $BACKUP_DIR/redis_dump.rdb
        print_status "Redis backup saved to $BACKUP_DIR/redis_dump.rdb"
    fi
    
    print_status "All backups completed in $BACKUP_DIR"
}

# Test cloud connections
test_connections() {
    print_status "Testing cloud service connections..."
    
    source .env.cloud
    
    # Test Supabase
    print_info "Testing Supabase connection..."
    if psql "$SUPABASE_DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1; then
        print_status "✓ Supabase connection successful"
    else
        print_error "✗ Supabase connection failed"
        return 1
    fi
    
    # Test Qdrant Cloud
    print_info "Testing Qdrant Cloud connection..."
    if curl -s -H "api-key: $QDRANT_CLOUD_API_KEY" $QDRANT_CLOUD_URL/collections > /dev/null; then
        print_status "✓ Qdrant Cloud connection successful"
    else
        print_error "✗ Qdrant Cloud connection failed"
        return 1
    fi
    
    # Test Temporal Cloud (basic check)
    print_info "Testing Temporal Cloud configuration..."
    if [ ! -z "$TEMPORAL_CLOUD_ENDPOINT" ] && [ ! -z "$TEMPORAL_CLOUD_NAMESPACE" ]; then
        print_status "✓ Temporal Cloud configuration present"
    else
        print_error "✗ Temporal Cloud configuration missing"
        return 1
    fi
    
    print_status "All cloud connections verified!"
}

# Migrate PostgreSQL to Supabase
migrate_postgres() {
    print_status "Migrating PostgreSQL to Supabase..."
    
    source .env.cloud
    
    if [ -f "backups/latest/postgres_backup.sql" ]; then
        print_info "Restoring database to Supabase..."
        psql "$SUPABASE_DATABASE_URL" < backups/latest/postgres_backup.sql
        print_status "PostgreSQL migration completed"
    else
        print_warning "No PostgreSQL backup found. Please run backup first."
    fi
}

# Migrate Qdrant to Qdrant Cloud
migrate_qdrant() {
    print_status "Migrating Qdrant to Qdrant Cloud..."
    
    source .env.cloud
    
    # First, create collection in Qdrant Cloud
    print_info "Creating collection in Qdrant Cloud..."
    curl -X PUT "$QDRANT_CLOUD_URL/collections/qlp_vectors" \
        -H "api-key: $QDRANT_CLOUD_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "vectors": {
                "size": 1536,
                "distance": "Cosine"
            }
        }'
    
    # Upload snapshot if exists
    if [ -f "backups/latest/qdrant_snapshot.tar" ]; then
        print_info "Uploading snapshot to Qdrant Cloud..."
        curl -X POST "$QDRANT_CLOUD_URL/collections/qlp_vectors/snapshots/upload" \
            -H "api-key: $QDRANT_CLOUD_API_KEY" \
            -F "snapshot=@backups/latest/qdrant_snapshot.tar"
        print_status "Qdrant migration completed"
    else
        print_warning "No Qdrant snapshot found. Collection created empty."
    fi
}

# Switch to cloud services
switch_to_cloud() {
    print_status "Switching to cloud services..."
    
    # Stop current services
    print_info "Stopping local services..."
    docker-compose -f docker-compose.platform.yml down
    
    # Use cloud environment
    cp .env.cloud .env
    
    # Start with cloud services
    print_info "Starting services with cloud backends..."
    docker-compose -f docker-compose.cloud-services.yml up -d
    
    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 30
    
    # Check health
    if curl -s http://localhost:8000/health > /dev/null; then
        print_status "✓ Services are running with cloud backends!"
    else
        print_error "✗ Services failed to start. Check logs."
        docker-compose -f docker-compose.cloud-services.yml logs
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "What would you like to do?"
    echo "1) Backup local data"
    echo "2) Test cloud connections"
    echo "3) Migrate PostgreSQL to Supabase"
    echo "4) Migrate Qdrant to Qdrant Cloud"
    echo "5) Switch to cloud services (full migration)"
    echo "6) Rollback to local services"
    echo "7) Exit"
    echo ""
    read -p "Enter your choice (1-7): " choice
}

# Rollback function
rollback() {
    print_warning "Rolling back to local services..."
    
    # Stop cloud services
    docker-compose -f docker-compose.cloud-services.yml down
    
    # Restore original .env if backed up
    if [ -f ".env.local-backup" ]; then
        cp .env.local-backup .env
    fi
    
    # Start local services
    docker-compose -f docker-compose.platform.yml up -d
    
    print_status "Rolled back to local services"
}

# Create symlink for latest backup
create_latest_symlink() {
    if [ -d "$BACKUP_DIR" ]; then
        rm -f backups/latest
        ln -s $(basename $BACKUP_DIR) backups/latest
    fi
}

# Main execution
main() {
    check_cloud_env
    
    while true; do
        show_menu
        
        case $choice in
            1)
                backup_data
                create_latest_symlink
                ;;
            2)
                test_connections
                ;;
            3)
                migrate_postgres
                ;;
            4)
                migrate_qdrant
                ;;
            5)
                print_warning "This will stop local services and switch to cloud."
                read -p "Are you sure? (yes/no): " confirm
                if [ "$confirm" == "yes" ]; then
                    # Backup current .env
                    cp .env .env.local-backup
                    backup_data
                    create_latest_symlink
                    test_connections && switch_to_cloud
                fi
                ;;
            6)
                rollback
                ;;
            7)
                print_status "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                ;;
        esac
    done
}

# Run main function
main