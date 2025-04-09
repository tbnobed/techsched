#!/bin/bash
set -e

# Function to wait for the PostgreSQL database to be ready
wait_for_postgres() {
  echo "Waiting for PostgreSQL to be ready..."
  
  local max_attempts=30
  local attempt=0
  local sleep_time=5
  
  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    echo "Attempt $attempt of $max_attempts..."
    
    if pg_isready -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
      echo "PostgreSQL is up and running!"
      return 0
    fi
    
    echo "PostgreSQL is not ready yet. Waiting $sleep_time seconds..."
    sleep $sleep_time
  done
  
  echo "Failed to connect to PostgreSQL after $max_attempts attempts."
  return 1
}

# Wait for PostgreSQL before starting the application
if [ "$1" = "python" ]; then
  wait_for_postgres
  echo "Starting the application..."
  exec "$@"
fi

# If the command does not start with python (e.g., bash, sh), execute it directly
exec "$@"