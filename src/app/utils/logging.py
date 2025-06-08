"""Logging utilities and middleware."""
import logging
import sys
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def setup_logging(level: str = "INFO", format_string: str | None = None) -> None:
    """Configure application logging."""
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
        )

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()), format=format_string, stream=sys.stdout
    )

    # Set specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Add custom filter for correlation ID
    for handler in logging.root.handlers:
        handler.addFilter(CorrelationIdFilter())


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        # Try to get correlation ID from context, otherwise use a default
        if not hasattr(record, "correlation_id"):
            record.correlation_id = getattr(self, "correlation_id", "no-correlation-id")
        return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests."""

    async def dispatch(self, request: Request, call_next: Callable):
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = f"req_{uuid.uuid4().hex[:12]}"

        # Store in request state
        request.state.correlation_id = correlation_id

        # Set for logging
        correlation_filter = CorrelationIdFilter()
        correlation_filter.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
