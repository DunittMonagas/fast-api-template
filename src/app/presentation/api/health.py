"""Health check endpoints."""
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends

from app.infrastructure.clients.google_ai_client import GoogleAIClient
from app.infrastructure.clients.telegram_client import TelegramClient
from app.infrastructure.database.session import DatabaseSession
from app.infrastructure.messaging.redis_publisher import RedisEventPublisher
from app.presentation.api.schemas import HealthCheckResponse

logger = logging.getLogger(__name__)


def create_health_router(
    db_session: DatabaseSession,
    redis_publisher: RedisEventPublisher,
    telegram_client: TelegramClient,
    google_ai_client: GoogleAIClient,
) -> APIRouter:
    """Create health check router with dependency injection."""

    router = APIRouter(
        prefix="/health",
        tags=["health"],
    )

    @router.get(
        "/",
        response_model=HealthCheckResponse,
        summary="Health check",
        description="Check the health status of the application and its dependencies",
    )
    async def health_check() -> HealthCheckResponse:
        """Check application health."""
        services_health = {}

        # Check database
        try:
            db_health = db_session.check_health()
            services_health["database"] = db_health
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            services_health["database"] = False

        # Check Redis
        try:
            redis_health = redis_publisher.check_health()
            services_health["redis"] = redis_health
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            services_health["redis"] = False

        # Check Telegram
        try:
            telegram_health = telegram_client.check_health()
            services_health["telegram"] = telegram_health
        except Exception as e:
            logger.error(f"Telegram health check failed: {e}")
            services_health["telegram"] = False

        # Check Google AI
        try:
            google_ai_health = google_ai_client.check_health()
            services_health["google_ai"] = google_ai_health
        except Exception as e:
            logger.error(f"Google AI health check failed: {e}")
            services_health["google_ai"] = False

        # Determine overall status
        all_healthy = all(services_health.values())
        status = "healthy" if all_healthy else "unhealthy"

        return HealthCheckResponse(
            status=status, timestamp=datetime.utcnow(), services=services_health
        )

    @router.get(
        "/live", summary="Liveness probe", description="Simple liveness check for Kubernetes"
    )
    async def liveness() -> Dict[str, str]:
        """Liveness probe endpoint."""
        return {"status": "alive"}

    @router.get("/ready", summary="Readiness probe", description="Readiness check for Kubernetes")
    async def readiness() -> Dict[str, str]:
        """Readiness probe endpoint."""
        # Check if database is ready
        try:
            if db_session.check_health():
                return {"status": "ready"}
            else:
                return {"status": "not ready", "reason": "database not healthy"}
        except Exception:
            return {"status": "not ready", "reason": "database check failed"}

    return router
