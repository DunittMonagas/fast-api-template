.PHONY: help build up down logs logs-worker shell shell-worker test test-db-up test-db-down test-unit test-integration test-cov format lint type-check migrate clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all services (API + Worker)"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - View API logs"
	@echo "  make logs-worker  - View worker logs"
	@echo "  make shell        - Open shell in API container"
	@echo "  make shell-worker - Open shell in worker container"
	@echo "  make test         - Run all tests"
	@echo "  make format       - Format code with black and isort"
	@echo "  make lint         - Run flake8 linter"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make migrate      - Run database migrations"
	@echo "  make clean        - Clean up generated files"
	@echo ""
	@echo "Production commands:"
	@echo "  make build-prod   - Build production images"
	@echo "  make run-prod     - Run production services"
	@echo "  make stop-prod    - Stop production services"

# Docker commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f app

logs-worker:
	docker compose logs -f worker

shell:
	docker compose exec app bash

shell-worker:
	docker compose exec worker bash

# Test database commands
test-db-up:
	docker compose -f docker-compose.test.yml up -d
	@echo "Waiting for test database to be ready..."
	@sleep 5

test-db-down:
	docker compose -f docker-compose.test.yml down -v

# Development commands
test: test-db-up
	docker run --rm --network="host" -v $(PWD)/src:/app/src -v $(PWD)/tests:/app/tests \
		-e POSTGRES_HOST=localhost -e POSTGRES_PORT=5433 -e POSTGRES_USER=testuser -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=test_db \
		-e REDIS_HOST=localhost -e REDIS_PORT=6380 \
		-e TELEGRAM_BOT_TOKEN=test_token -e GOOGLE_API_KEY=test_key \
		-e PYTHONPATH=/app/src \
		fast-api-template-app pytest
	@make test-db-down

test-unit:
	docker compose run --rm app pytest tests/unit -v

test-integration: test-db-up
	docker run --rm --network="host" -v $(PWD)/src:/app/src -v $(PWD)/tests:/app/tests \
		-e POSTGRES_HOST=localhost -e POSTGRES_PORT=5433 -e POSTGRES_USER=testuser -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=test_db \
		-e REDIS_HOST=localhost -e REDIS_PORT=6380 \
		-e TELEGRAM_BOT_TOKEN=test_token -e GOOGLE_API_KEY=test_key \
		-e PYTHONPATH=/app/src \
		fast-api-template-app pytest tests/integration -v
	@make test-db-down

test-cov: test-db-up
	docker run --rm --network="host" -v $(PWD)/src:/app/src -v $(PWD)/tests:/app/tests \
		-e POSTGRES_HOST=localhost -e POSTGRES_PORT=5433 -e POSTGRES_USER=testuser -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=test_db \
		-e REDIS_HOST=localhost -e REDIS_PORT=6380 \
		-e TELEGRAM_BOT_TOKEN=test_token -e GOOGLE_API_KEY=test_key \
		-e PYTHONPATH=/app/src \
		fast-api-template-app pytest --cov=app --cov-report=html --cov-report=term
	@make test-db-down

format:
	docker compose run --rm app black src tests
	docker compose run --rm app isort src tests

lint:
	docker compose run --rm app flake8 src tests

type-check:
	docker compose run --rm app mypy src

# Database commands
migrate:
	docker compose run --rm app alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	docker compose run --rm app alembic revision --autogenerate -m "$$msg"

migrate-down:
	docker compose run --rm app alembic downgrade -1

# Utility commands
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Production commands
build-prod:
	docker build -f Dockerfile.prod -t fastapi-app:latest .
	docker build -f Dockerfile.worker -t fastapi-worker:latest .

build-prod-api:
	docker build -f Dockerfile.prod -t fastapi-app:latest .

build-prod-worker:
	docker build -f Dockerfile.worker -t fastapi-worker:latest .

run-prod:
	docker compose -f docker-compose.prod.yml up -d

run-prod-api:
	docker run -d --name fastapi-api -p 8000:8000 --env-file .env.production fastapi-app:latest

run-prod-worker:
	docker run -d --name fastapi-worker --env-file .env.production fastapi-worker:latest

stop-prod:
	docker compose -f docker-compose.prod.yml down 