#!/bin/bash

# Exit on any error
set -e

echo "Starting application with automated migrations..."

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if database is ready
wait_for_db() {
    log "Waiting for database to be ready..."
    
    # Try to connect to database using alembic
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import sys
sys.path.append('/app')
from alembic import command
from alembic.config import Config
try:
    config = Config('alembic.ini')
    command.current(config)
    print('Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log "Database is ready!"
            return 0
        fi
        
        log "Database not ready yet (attempt $attempt/$max_attempts). Waiting 2 seconds..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log "ERROR: Database failed to become ready after $max_attempts attempts"
    exit 1
}

# Function to run migrations
run_migrations() {
    log "Checking migration status..."
    
    # Simple approach: just run alembic upgrade head
    # Alembic is smart enough to handle both new databases and existing ones
    log "Running alembic upgrade head..."
    
    if alembic upgrade head; then
        log "Migration completed successfully!"
        return 0
    else
        log "ERROR: Migration failed!"
        exit 1
    fi
}

# Function to create default admin user
create_default_user() {
    log "Creating default admin user if needed..."
    
    # Set Python path to include the current directory so 'app' module can be found
    if PYTHONPATH=/app python scripts/create_first_user.py; then
        log "Default admin user setup completed!"
        return 0
    else
        log "ERROR: Failed to create default admin user!"
        exit 1
    fi
}

# Function to start the application
start_application() {
    log "Starting FastAPI application..."
    exec "$@"
}

# Main execution flow
main() {
    log "=== Automated Migration and Startup Script ==="
    
    # Wait for database to be ready
    wait_for_db
    
    # Run migrations if needed
    run_migrations
    
    # Create default admin user if needed
    create_default_user
    
    # Start the application
    start_application "$@"
}

# Run main function with all arguments passed to script
main "$@"