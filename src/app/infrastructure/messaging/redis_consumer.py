"""Redis consumer base class for consuming messages from streams."""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

import redis

from app.config import Settings

logger = logging.getLogger(__name__)


class RedisStreamConsumer(ABC):
    """Base class for Redis stream consumers."""

    def __init__(
        self,
        settings: Settings,
        stream_key: str,
        consumer_group: str,
        consumer_name: str,
        block_ms: int = 1000,
    ):
        self.settings = settings
        self.stream_key = stream_key
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.block_ms = block_ms
        self._client: redis.Redis | None = None
        self._running = False

    def initialize(self) -> None:
        """Initialize Redis connection and create consumer group."""
        if self._client is not None:
            return

        logger.info(f"Initializing Redis consumer: {self.consumer_name}")

        self._client = redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            db=self.settings.redis_db,
            password=self.settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={},
        )

        # Create consumer group if it doesn't exist
        try:
            self._client.xgroup_create(self.stream_key, self.consumer_group, id="0", mkstream=True)
            logger.info(f"Created consumer group: {self.consumer_group}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group {self.consumer_group} already exists")
            else:
                raise

    def close(self) -> None:
        """Close Redis connection."""
        self._running = False
        if self._client is not None:
            logger.info(f"Closing Redis consumer: {self.consumer_name}")
            self._client.close()
            self._client = None

    @abstractmethod
    def process_message(self, message_id: str, data: Dict[str, Any]) -> None:
        """Process a single message. Must be implemented by subclasses."""
        pass

    def run(self) -> None:
        """Run the consumer loop (blocking)."""
        if self._client is None:
            raise RuntimeError("Consumer not initialized")

        self._running = True
        logger.info(f"Starting consumer {self.consumer_name} for stream {self.stream_key}")

        while self._running:
            try:
                # Read messages from stream
                messages = self._client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_key: ">"},
                    count=10,
                    block=self.block_ms,
                )

                if messages:
                    for stream_name, stream_messages in messages:
                        for message_id, data in stream_messages:
                            try:
                                # Parse message data
                                parsed_data = self._parse_message(data)

                                # Process message
                                self.process_message(message_id, parsed_data)

                                # Acknowledge message
                                self._client.xack(self.stream_key, self.consumer_group, message_id)

                            except Exception as e:
                                logger.error(f"Error processing message {message_id}: {e}")
                                # Don't acknowledge - message will be redelivered

            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                if self._running:
                    # Sleep before retrying
                    import time

                    time.sleep(1)

    async def run_async(self) -> None:
        """Run the consumer loop asynchronously."""
        # Run the synchronous consumer in a thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.run)

    def stop(self) -> None:
        """Stop the consumer loop."""
        logger.info(f"Stopping consumer {self.consumer_name}")
        self._running = False

    def _parse_message(self, data: Dict[str, str]) -> Dict[str, Any]:
        """Parse message data, converting JSON strings back to dicts."""
        parsed = {}
        for key, value in data.items():
            try:
                # Try to parse as JSON
                if value.startswith("{") or value.startswith("["):
                    parsed[key] = json.loads(value)
                else:
                    parsed[key] = value
            except (json.JSONDecodeError, AttributeError):
                parsed[key] = value
        return parsed


class ConsumerRegistry:
    """Registry for managing multiple consumers."""

    def __init__(self):
        self._consumers: Dict[str, RedisStreamConsumer] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def register(self, name: str, consumer: RedisStreamConsumer) -> None:
        """Register a consumer."""
        if name in self._consumers:
            raise ValueError(f"Consumer {name} already registered")
        self._consumers[name] = consumer
        logger.info(f"Registered consumer: {name}")

    async def start_all(self) -> None:
        """Start all registered consumers."""
        for name, consumer in self._consumers.items():
            consumer.initialize()
            task = asyncio.create_task(consumer.run_async())
            self._tasks[name] = task
            logger.info(f"Started consumer: {name}")

    async def stop_all(self) -> None:
        """Stop all running consumers."""
        # Signal all consumers to stop
        for consumer in self._consumers.values():
            consumer.stop()

        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        # Close all consumers
        for consumer in self._consumers.values():
            consumer.close()

        logger.info("All consumers stopped")
