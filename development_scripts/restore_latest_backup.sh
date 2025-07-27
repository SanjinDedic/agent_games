#!/bin/bash

# Configuration
SERVER_HOST="vccfinal.net"
SERVER_USER="ubuntu"
SSH_KEY="~/site_2024.pem"
REMOTE_BACKUP_DIR="~/db_backups"
LOCAL_DOWNLOAD_DIR="~/Downloads"
ENV_FILE="$HOME/Documents/PROJECTS/agent_games/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Database Restore Script ===${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run psql via Docker
docker_psql() {
    docker exec -i agent_games-postgres-1 psql -U postgres "$@"
}

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    print_error ".env file not found at $ENV_FILE"
    exit 1
fi

# Read DATABASE_URL from .env file
DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$DATABASE_URL" ]; then
    print_error "DATABASE_URL not found in .env file"
    exit 1
fi

# Extract database name for operations
DB_NAME=$(echo "$DATABASE_URL" | sed 's/.*\///')
print_status "Target database: $DB_NAME"

# Check if SSH key exists
if [ ! -f "${SSH_KEY/\~/$HOME}" ]; then
    print_error "SSH key not found at $SSH_KEY"
    exit 1
fi

# Check if Docker container is running
if ! docker ps | grep -q "agent_games-postgres-1"; then
    print_error "PostgreSQL Docker container is not running"
    print_error "Please start it with: docker compose --profile dev up -d"
    exit 1
fi

# Step 1: Find the latest backup on the server
print_status "Finding latest backup on server..."
LATEST_BACKUP=$(ssh -i "${SSH_KEY/\~/$HOME}" "$SERVER_USER@$SERVER_HOST" \
    "ls -t $REMOTE_BACKUP_DIR/agent_games_backup_*.sql 2>/dev/null | head -1")

if [ -z "$LATEST_BACKUP" ]; then
    print_error "No backup files found on server"
    exit 1
fi

BACKUP_FILENAME=$(basename "$LATEST_BACKUP")
print_status "Latest backup found: $BACKUP_FILENAME"

# Step 2: Copy the backup to local Downloads directory
print_status "Copying backup to local Downloads directory..."
LOCAL_BACKUP_PATH="${LOCAL_DOWNLOAD_DIR/\~/$HOME}/$BACKUP_FILENAME"

scp -i "${SSH_KEY/\~/$HOME}" "$SERVER_USER@$SERVER_HOST:$LATEST_BACKUP" "$LOCAL_BACKUP_PATH"

if [ $? -ne 0 ]; then
    print_error "Failed to copy backup file"
    exit 1
fi

print_status "Backup copied to: $LOCAL_BACKUP_PATH"

# Step 3: Check if backup file exists and is not empty
if [ ! -s "$LOCAL_BACKUP_PATH" ]; then
    print_error "Backup file is empty or doesn't exist"
    exit 1
fi

# Step 4: Prompt user for confirmation
echo
print_warning "This will completely replace your local '$DB_NAME' database!"
print_warning "All existing data will be lost."
echo
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_status "Operation cancelled by user"
    exit 0
fi

# Step 5: Test PostgreSQL connection
print_status "Testing PostgreSQL connection..."
if ! docker_psql -d postgres -c "SELECT 1;" >/dev/null 2>&1; then
    print_error "Cannot connect to PostgreSQL in Docker container"
    print_error "Please ensure the container is healthy: docker compose ps"
    exit 1
fi

# Step 6: Terminate active connections and drop/recreate database
print_status "Terminating active connections to database..."
docker_psql -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
    >/dev/null 2>&1

print_status "Dropping and recreating database..."
docker_psql -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" >/dev/null 2>&1
docker_psql -d postgres -c "CREATE DATABASE $DB_NAME;" >/dev/null 2>&1

if [ $? -ne 0 ]; then
    print_error "Failed to recreate database"
    exit 1
fi

# Step 7: Copy backup file into container and restore
print_status "Copying backup file to container..."
docker cp "$LOCAL_BACKUP_PATH" agent_games-postgres-1:/tmp/restore.sql

print_status "Restoring database from backup..."
docker_psql -d "$DB_NAME" -f /tmp/restore.sql >/dev/null

if [ $? -ne 0 ]; then
    print_error "Failed to restore database"
    print_warning "Check the backup file format and PostgreSQL logs"
    exit 1
fi

# Clean up temporary file in container
docker exec agent_games-postgres-1 rm -f /tmp/restore.sql

# Step 8: Verify the restore
print_status "Verifying database restore..."
TABLE_COUNT=$(docker_psql -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)

if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq 0 ]; then
    print_warning "No tables found in restored database - this might be normal if the backup was empty"
else
    print_status "Database restored successfully with $TABLE_COUNT tables"
fi

# Step 9: Show summary
echo
print_status "=== Restore Summary ==="
print_status "Remote backup: $LATEST_BACKUP"
print_status "Local backup copy: $LOCAL_BACKUP_PATH"
print_status "Database: $DB_NAME"
print_status "Tables restored: ${TABLE_COUNT:-0}"

# Optional: Show some database info
print_status "=== Database Info ==="
docker_psql -d "$DB_NAME" -c \
    "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;" \
    2>/dev/null || print_warning "Could not retrieve table information"

print_status "Restore completed successfully!"