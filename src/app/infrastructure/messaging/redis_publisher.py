"""Redis publisher implementation for event publishing."""
import json
import logging
from typing import Any, Dict

import redis

from app.application.repositories import EventPublisher
from app.config import Settings

logger = logging.getLogger(__name__)


class RedisEventPublisher(EventPublisher):
    """Redis implementation of EventPublisher using Redis Streams."""

    def __init__(self, settings: Settings, stream_key: str = "events"):
        self.settings = settings
        self.stream_key = stream_key
        self._client: redis.Redis | None = None

    def initialize(self) -> None:
        """Initialize Redis connection."""
        if self._client is not None:
            return

        logger.info("Initializing Redis event publisher")

        self._client = redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            db=self.settings.redis_db,
            password=self.settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={},
            connection_pool=redis.ConnectionPool(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                max_connections=self.settings.redis_pool_size,
                decode_responses=True,
            ),
        )

        # Test connection
        self._client.ping()
        logger.info("Redis event publisher initialized successfully")

    def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            logger.info("Closing Redis event publisher")
            self._client.close()
            self._client = None

    def publish(self, event_type: str, event_data: dict) -> None:
        """Publish an event to Redis stream."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized")

        try:
            # Prepare message data
            message = {"event_type": event_type, "data": json.dumps(event_data)}

            # Add to stream
            message_id = self._client.xadd(self.stream_key, message)

            logger.info(
                f"Published event {event_type} to stream {self.stream_key} with ID {message_id}"
            )

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            raise

    def check_health(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if self._client is None:
                return False
            self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


class RedisStreamPublisher:
    """Generic Redis stream publisher for specific streams."""

    def __init__(self, redis_client: redis.Redis, stream_key: str):
        self.redis_client = redis_client
        self.stream_key = stream_key

    def publish(self, message: Dict[str, Any]) -> str:
        """Publish a message to the stream."""
        # Convert nested dictionaries to JSON strings
        processed_message = {}
        for key, value in message.items():
            if isinstance(value, dict):
                processed_message[key] = json.dumps(value)
            else:
                processed_message[key] = str(value)

        # Add to stream
        message_id = self.redis_client.xadd(self.stream_key, processed_message)
        logger.info(f"Published message to stream {self.stream_key} with ID {message_id}")

        return message_id
