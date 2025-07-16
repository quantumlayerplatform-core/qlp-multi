#\!/bin/bash
# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker exec qlp-postgres pg_isready -U qlp_user -d qlp_db > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL is ready. Initializing database..."
python init_db_docker.py

if [ $? -eq 0 ]; then
  echo "Database initialization completed successfully"
else
  echo "Database initialization failed"
  exit 1
fi
EOF < /dev/null