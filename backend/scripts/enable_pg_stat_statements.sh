#!/bin/bash
# Quick Fix: Enable pg_stat_statements for Query Performance Monitoring
# Time Required: 15 minutes
# Impact: Enables N+1 detection and slow query analysis

set -e

echo "🔧 Enabling pg_stat_statements for Tattoo Studio System"
echo "========================================================"
echo ""

# Step 1: Check if extension exists
echo "📊 Step 1: Checking if extension is created..."
docker-compose exec db psql -U admin -d tattoo_studio -c \
  "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') as exists;"

# Step 2: Stop the database
echo ""
echo "🛑 Step 2: Stopping database container..."
docker-compose stop db

# Step 3: Update postgresql.conf
echo ""
echo "📝 Step 3: Updating PostgreSQL configuration..."
echo "Note: This needs to be done manually in Docker volume or via custom config file"
echo ""
echo "Add the following to postgresql.conf:"
echo "  shared_preload_libraries = 'pg_stat_statements'"
echo "  pg_stat_statements.track = all"
echo "  pg_stat_statements.max = 10000"
echo ""
echo "For Docker, add to docker-compose.yml under db service:"
echo ""
cat << 'EOF'
services:
  db:
    image: postgres:16
    command: postgres -c shared_preload_libraries=pg_stat_statements
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secret123}
      POSTGRES_DB: ${POSTGRES_DB:-tattoo_studio}
EOF
echo ""
read -p "Press Enter after updating docker-compose.yml..."

# Step 4: Start database with new config
echo ""
echo "🚀 Step 4: Restarting database with new configuration..."
docker-compose up -d db

echo ""
echo "⏳ Waiting for database to be ready (30 seconds)..."
sleep 30

# Step 5: Verify extension is loaded
echo ""
echo "✅ Step 5: Verifying pg_stat_statements is loaded..."
docker-compose exec db psql -U admin -d tattoo_studio -c \
  "SELECT COUNT(*) as query_count FROM pg_stat_statements;"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! pg_stat_statements is now enabled!"
    echo ""
    echo "📊 You can now use the analysis scripts:"
    echo "  python -m app.core.pg_stats_setup --top-slow 10"
    echo "  python -m app.core.pg_stats_setup --most-frequent 20"
    echo "  python -m app.core.pg_stats_setup --detect-n-plus-one"
else
    echo ""
    echo "❌ ERROR: pg_stat_statements is not loaded"
    echo "Check the PostgreSQL logs:"
    echo "  docker-compose logs db | tail -50"
fi

echo ""
echo "========================================================"
echo "Configuration complete!"
