#!/bin/bash
# Script to create test database if it doesn't exist

set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=testpass psql -h localhost -p 5433 -U testuser -d postgres -c '\q' 2>/dev/null; do
  sleep 1
done

# Check if test database exists
if ! PGPASSWORD=testpass psql -h localhost -p 5433 -U testuser -lqt | cut -d \| -f 1 | grep -qw test_test_db; then
    echo "Creating test database..."
    PGPASSWORD=testpass psql -h localhost -p 5433 -U testuser -d postgres -c "CREATE DATABASE test_test_db;"
    echo "Test database created successfully"
else
    echo "Test database already exists"
fi 