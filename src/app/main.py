"""Main FastAPI application entry point."""
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.application.services.task_service import TaskService
from app.config import get_settings
from app.domain.exceptions import DomainException
from app.infrastructure.clients.google_ai_client import GoogleAIClient
from app.infrastructure.clients.telegram_client import TelegramClient
from app.infrastructure.database.repositories.task_repository import SQLAlchemyTaskRepository
from app.infrastructure.database.session import DatabaseSession
from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from app.infrastructure.messaging.redis_consumer import ConsumerRegistry
from app.infrastructure.messaging.redis_publisher import RedisEventPublisher
from app.presentation.api.health import create_health_router
from app.presentation.api.tasks import create_task_router
from app.presentation.consumers.task_notification_consumer import TaskNotificationConsumer
from app.utils.logging import CorrelationIdMiddleware, setup_logging

# Initialize logging
logger = logging.getLogger(__name__)

# Global references for cleanup
consumer_registry: ConsumerRegistry | None = None
db_session: DatabaseSession | None = None
redis_publisher: RedisEventPublisher | None = None
telegram_client: TelegramClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage application lifecycle."""
    global consumer_registry, db_session, redis_publisher, telegram_client

    logger.info("Starting application...")

    # Get settings
    settings = get_settings()

    # Initialize infrastructure
    logger.info("Initializing infrastructure...")

    # Database
    db_session = DatabaseSession(settings)
    db_session.initialize()

    # Create tables (in production, use Alembic migrations instead)
    if settings.is_development:
        db_session.create_tables()

    # Redis
    redis_publisher = RedisEventPublisher(settings)
    redis_publisher.initialize()

    # External clients
    telegram_client = TelegramClient(settings)
    google_ai_client = GoogleAIClient(settings)

    # Create repositories and services
    task_repository = SQLAlchemyTaskRepository(db_session)
    unit_of_work = SQLAlchemyUnitOfWork(db_session)

    task_service = TaskService(
        task_repository=task_repository, unit_of_work=unit_of_work, event_publisher=redis_publisher
    )

    # Register API routers
    app.include_router(create_task_router(task_service), prefix=settings.api_prefix)
    app.include_router(
        create_health_router(db_session, redis_publisher, telegram_client, google_ai_client),
        prefix=settings.api_prefix,
    )

    # Initialize and start consumers
    if settings.run_consumers_in_api:
        consumer_registry = ConsumerRegistry()

        # Create notification consumer (only if chat ID is configured)
        notification_chat_id = (
            settings.telegram_notification_chat_id
            if hasattr(settings, "telegram_notification_chat_id")
            else None
        )
        if notification_chat_id:
            notification_consumer = TaskNotificationConsumer(
                settings=settings,
                telegram_client=telegram_client,
                notification_chat_id=notification_chat_id,
            )
            consumer_registry.register("task-notifications", notification_consumer)

        # Start all consumers
        await consumer_registry.start_all()
        logger.info("Consumers started in API process")
    else:
        logger.info("Consumers will run in separate worker process")

    logger.info("Application started successfully")

    yield

    # Cleanup
    logger.info("Shutting down application...")

    # Stop consumers
    if consumer_registry:
        await consumer_registry.stop_all()

    # Close connections
    if redis_publisher:
        redis_publisher.close()
    if db_session:
        db_session.close()
    if telegram_client:
        telegram_client.close()

    logger.info("Application shut down complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Setup logging
    setup_logging(settings.log_level, settings.log_format)

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description="FastAPI project following DDD and Clean Architecture",
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Add correlation ID middleware
    app.add_middleware(CorrelationIdMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Global exception handler for domain exceptions
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
                "request_id": request.state.correlation_id,
            },
        )

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "environment": settings.app_env.value,
            "version": "1.0.0",
        }

    return app


def handle_shutdown(signum, frame):
    """Handle graceful shutdown."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)


# Create the application instance
app = create_app()


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Run the application
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
