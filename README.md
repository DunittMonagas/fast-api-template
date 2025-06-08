# FastAPI DDD Template

A production-ready FastAPI project template following Domain-Driven Design (DDD) principles and Clean Architecture patterns. This template provides a robust foundation for building scalable microservices with clear separation of concerns.

## 🏗️ Architecture Overview

This project strictly follows **Domain-Driven Design (DDD)** and **Clean Architecture** principles:

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│                  (FastAPI Routes & Consumers)                │
├─────────────────────────────────────────────────────────────┤
│                     Application Layer                        │
│                   (Use Cases & Services)                     │
├─────────────────────────────────────────────────────────────┤
│                       Domain Layer                           │
│                 (Entities & Business Logic)                  │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│              (Database, Redis, External APIs)                │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

- **Domain-Driven Design**: Business logic is encapsulated in the domain layer
- **Clean Architecture**: Dependencies point inward (infrastructure → application → domain)
- **Synchronous Database Access**: Uses psycopg3 for synchronous PostgreSQL operations
- **Event-Driven**: Domain events are published to Redis streams
- **SOLID Principles**: Single responsibility, dependency injection, interface segregation

## 📁 Project Structure

```
fast-api-template/
├── src/
│   └── app/
│       ├── domain/              # Core business logic
│       │   ├── models.py        # Domain entities
│       │   ├── events.py        # Domain events
│       │   └── exceptions.py    # Domain-specific exceptions
│       ├── application/         # Use cases layer
│       │   ├── services/        # Application services
│       │   └── repositories.py  # Repository interfaces (abstractions)
│       ├── infrastructure/      # External concerns
│       │   ├── database/        # Database implementations
│       │   │   ├── models.py    # ORM models
│       │   │   ├── repositories/# Concrete repository implementations
│       │   │   ├── session.py   # Database session management
│       │   │   └── connection.py# Connection pooling
│       │   ├── messaging/       # Redis pub/sub
│       │   └── clients/         # External API clients
│       ├── presentation/        # External interfaces
│       │   ├── api/            # FastAPI routes
│       │   └── consumers/      # Redis stream consumers
│       ├── utils/              # Shared utilities
│       ├── config.py           # Application configuration
│       └── main.py             # Application entry point
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── alembic/                    # Database migrations
├── docker compose.yml          # Development environment
├── Dockerfile.dev              # Development container
├── Dockerfile.prod             # Production container
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
└── .vscode/                    # VS Code configuration
    └── launch.json             # Debug configurations
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- VS Code (recommended for debugging)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fast-api-template
   ```

2. **Create environment file**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start the development environment**
   ```bash
   docker compose up -d
   ```
   
   This starts:
   - API service (port 8000)
   - Worker service (for processing events)
   - PostgreSQL database
   - Redis

4. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - pgAdmin: http://localhost:5050 (with profile: `docker compose --profile tools up`)
   - Redis Commander: http://localhost:8081 (with profile: `docker compose --profile tools up`)

### Remote Debugging with VS Code

The development setup includes debugpy for remote debugging:

1. Start the containers: `docker compose up`
2. In VS Code, open the Run and Debug panel (Ctrl+Shift+D)
3. Select "Python: Remote Attach to Docker" configuration
4. Press F5 to attach the debugger
5. Set breakpoints in your code and debug as usual

### Working with API and Worker Services

In development, the API and worker run as separate containers:

```bash
# View API logs
make logs

# View worker logs
make logs-worker

# Access API container shell
make shell

# Access worker container shell
make shell-worker

# Debug API on port 5678
# Debug Worker on port 5679
```

Both services can be debugged simultaneously using VS Code's multi-target debugging.

## 🔧 Development

### Running Tests

```bash
# Run all tests
docker compose run --rm app pytest

# Run with coverage
docker compose run --rm app pytest --cov=app --cov-report=html

# Run specific test file
docker compose run --rm app pytest tests/unit/test_task_service.py
```

### Database Migrations

```bash
# Create a new migration
docker compose run --rm app alembic revision --autogenerate -m "Description"

# Apply migrations
docker compose run --rm app alembic upgrade head

# Rollback one migration
docker compose run --rm app alembic downgrade -1
```

### Code Quality

```bash
# Format code
docker compose run --rm app black src tests

# Sort imports
docker compose run --rm app isort src tests

# Type checking
docker compose run --rm app mypy src

# Linting
docker compose run --rm app flake8 src tests
```

## 📋 API Endpoints

### Tasks

- `POST /api/v1/tasks` - Create a new task
- `GET /api/v1/tasks/{task_id}` - Get a task by ID
- `GET /api/v1/tasks` - List tasks with filtering
- `PATCH /api/v1/tasks/{task_id}` - Update task details
- `POST /api/v1/tasks/{task_id}/start` - Start a task
- `POST /api/v1/tasks/{task_id}/complete` - Complete a task
- `POST /api/v1/tasks/{task_id}/cancel` - Cancel a task
- `POST /api/v1/tasks/{task_id}/assign` - Assign a task
- `DELETE /api/v1/tasks/{task_id}` - Delete a task
- `GET /api/v1/tasks/statistics` - Get task statistics

### Health Checks

- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe

## 🏭 Production Deployment

### Architecture

In production, the application runs as two separate services:
- **API Service**: Handles HTTP requests
- **Worker Service**: Processes Redis stream events

This separation allows for:
- Independent scaling of API and workers
- Better fault isolation
- Optimized resource allocation

### Building Production Images

```bash
# Build both images
make build-prod

# Or build individually
docker build -f Dockerfile.prod -t fastapi-app:latest .
docker build -f Dockerfile.worker -t fastapi-worker:latest .
```

### Running with Docker Compose

```bash
# Start all production services
make run-prod

# Or using docker compose directly
docker compose -f docker compose.prod.yml up -d

# Stop services
make stop-prod
```

### Running Without Docker Compose

You can run each service independently using Docker:

```bash
# Run PostgreSQL
docker run -d \
  --name postgres-db \
  -e POSTGRES_USER=produser \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=proddb \
  -p 5432:5432 \
  postgres:16-alpine

# Run Redis
docker run -d \
  --name redis-cache \
  -p 6379:6379 \
  redis:7-alpine redis-server --requirepass your_redis_password

# Run API
docker run -d \
  --name fastapi-api \
  -p 8000:8000 \
  --env-file .env.production \
  --link postgres-db:db \
  --link redis-cache:redis \
  fastapi-app:latest

# Run Worker
docker run -d \
  --name fastapi-worker \
  --env-file .env.production \
  --link postgres-db:db \
  --link redis-cache:redis \
  fastapi-worker:latest
```

### Environment Variables

Key production variables (see `env.production.example`):
- `APP_ENV`: Must be `production`
- `RUN_CONSUMERS_IN_API`: Must be `false` (consumers run separately)
- `POSTGRES_*`: PostgreSQL connection settings
- `REDIS_*`: Redis connection settings
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for notifications
- `GOOGLE_API_KEY`: Google AI API key

### Production Considerations

1. **Database Migrations**: Run Alembic migrations before deploying
   ```bash
   docker run --rm --env-file .env.production fastapi-app:latest alembic upgrade head
   ```

2. **Secrets Management**: Use proper secret management (e.g., AWS Secrets Manager, Vault)

3. **Monitoring**: 
   - Monitor both API and worker containers
   - Track Redis stream lag
   - Set up alerts for consumer failures

4. **Logging**: Configure centralized logging (ELK stack, CloudWatch)

5. **Scaling**:
   - Scale API based on HTTP traffic
   - Scale workers based on message queue depth
   
6. **Health Checks**:
   - API: `GET /api/v1/health`
   - Worker: Monitor consumer processing rate

7. **Rate Limiting**: Adjust rate limits based on your needs

8. **CORS**: Configure allowed origins for your frontend

## 🔌 External Integrations

### Redis Streams

The application uses Redis streams for event-driven architecture:
- Domain events are published to the `events` stream
- Consumers can process events asynchronously
- Example: `TaskNotificationConsumer` sends Telegram notifications

### Telegram Bot

Configure your Telegram bot token and chat ID to receive notifications:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_NOTIFICATION_CHAT_ID=your_chat_id
```

### Google AI

The template includes a client for Google's Generative AI:
```python
# Example usage
response = google_ai_client.generate_text(
    prompt="Generate a task description",
    temperature=0.7
)
```

## 🧪 Testing Strategy

### Unit Tests
- Test business logic in isolation
- Mock external dependencies
- Located in `tests/unit/`

### Integration Tests
- Test repository implementations
- Use test database
- Located in `tests/integration/`

### End-to-End Tests
- Test complete user flows
- Use TestClient
- Can be added in `tests/e2e/`

## 🔒 Security

- **Authentication**: Implement JWT or OAuth2 (not included in template)
- **Rate Limiting**: Configured via SlowAPI
- **CORS**: Configurable allowed origins
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, etc.
- **Input Validation**: Pydantic models validate all inputs

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Domain-Driven Design Reference](https://www.domainlanguage.com/ddd/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/)

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
