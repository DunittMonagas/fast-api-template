"""Standalone worker for running Redis stream consumers."""
import asyncio
import logging
import signal
import sys
from typing import Optional

from app.config import get_settings
from app.infrastructure.clients.telegram_client import TelegramClient
from app.infrastructure.messaging.redis_consumer import ConsumerRegistry
from app.presentation.consumers.task_notification_consumer import TaskNotificationConsumer
from app.utils.logging import setup_logging

# Initialize logging
logger = logging.getLogger(__name__)

# Global registry for cleanup
consumer_registry: Optional[ConsumerRegistry] = None


async def setup_consumers() -> ConsumerRegistry:
    """Set up and register all consumers."""
    settings = get_settings()
    registry = ConsumerRegistry()

    # Initialize clients
    telegram_client = TelegramClient(settings)

    # Register notification consumer if configured
    if settings.telegram_notification_chat_id:
        notification_consumer = TaskNotificationConsumer(
            settings=settings,
            telegram_client=telegram_client,
            notification_chat_id=settings.telegram_notification_chat_id,
        )
        registry.register("task-notifications", notification_consumer)
        logger.info("Registered task notification consumer")
    else:
        logger.warning(
            "Telegram notification chat ID not configured, skipping notification consumer"
        )

    # Add more consumers here as needed
    # Example:
    # if settings.enable_email_consumer:
    #     email_consumer = EmailNotificationConsumer(settings)
    #     registry.register("email-notifications", email_consumer)

    return registry


async def main():
    """Main worker entry point."""
    global consumer_registry

    # Setup logging
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    logger.info(f"Starting worker in {settings.app_env} environment")

    try:
        # Setup consumers
        consumer_registry = await setup_consumers()

        if not consumer_registry._consumers:
            logger.error("No consumers registered. Please check configuration.")
            return

        # Start all consumers
        await consumer_registry.start_all()
        logger.info("All consumers started successfully")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        if consumer_registry:
            logger.info("Stopping all consumers...")
            await consumer_registry.stop_all()
        logger.info("Worker shutdown complete")


def handle_shutdown(signum, frame):
    """Handle graceful shutdown."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    # Cancel all tasks
    loop = asyncio.get_event_loop()
    for task in asyncio.all_tasks(loop):
        task.cancel()


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Run the worker
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
