#!/bin/bash
# Script to demonstrate running services without docker compose
# This shows how to run each service independently

set -e

echo "This script demonstrates how to run services without docker compose"
echo "Make sure to update the environment variables and connection strings!"
echo ""

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

# Create a Docker network
echo "Creating Docker network..."
docker network create fastapi-network 2>/dev/null || true

# Run PostgreSQL
echo "Starting PostgreSQL..."
docker run -d \
  --name postgres-db \
  --network fastapi-network \
  -e POSTGRES_USER=${POSTGRES_USER:-produser} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-strongpassword} \
  -e POSTGRES_DB=${POSTGRES_DB:-proddb} \
  -p 5432:5432 \
  --restart unless-stopped \
  postgres:16-alpine

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Run Redis
echo "Starting Redis..."
docker run -d \
  --name redis-cache \
  --network fastapi-network \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:7-alpine redis-server --requirepass ${REDIS_PASSWORD:-""}

# Build images if not exists
echo "Building images..."
docker build -f Dockerfile.prod -t fastapi-app:latest .
docker build -f Dockerfile.worker -t fastapi-worker:latest .

# Run database migrations
echo "Running database migrations..."
docker run --rm \
  --network fastapi-network \
  -e POSTGRES_HOST=postgres-db \
  -e REDIS_HOST=redis-cache \
  --env-file .env.production \
  fastapi-app:latest \
  alembic upgrade head

# Run API
echo "Starting API service..."
docker run -d \
  --name fastapi-api \
  --network fastapi-network \
  -p 8000:8000 \
  -e POSTGRES_HOST=postgres-db \
  -e REDIS_HOST=redis-cache \
  -e RUN_CONSUMERS_IN_API=false \
  --env-file .env.production \
  --restart unless-stopped \
  fastapi-app:latest

# Run Worker
echo "Starting Worker service..."
docker run -d \
  --name fastapi-worker \
  --network fastapi-network \
  -e POSTGRES_HOST=postgres-db \
  -e REDIS_HOST=redis-cache \
  --env-file .env.production \
  --restart unless-stopped \
  fastapi-worker:latest

echo ""
echo "All services started!"
echo "API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To check status: docker ps"
echo "To view logs: docker logs -f <container-name>"
echo "To stop all: docker stop fastapi-api fastapi-worker postgres-db redis-cache"
echo "To remove all: docker rm fastapi-api fastapi-worker postgres-db redis-cache" 