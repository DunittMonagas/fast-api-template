"""Task notification consumer - handles task events and sends notifications."""
import json
import logging
from typing import Any, Dict

from app.config import Settings
from app.infrastructure.clients.telegram_client import TelegramClient
from app.infrastructure.messaging.redis_consumer import RedisStreamConsumer

logger = logging.getLogger(__name__)


class TaskNotificationConsumer(RedisStreamConsumer):
    """Consumer that listens for task events and sends notifications."""

    def __init__(
        self, settings: Settings, telegram_client: TelegramClient, notification_chat_id: str
    ):
        super().__init__(
            settings=settings,
            stream_key="events",  # Listen to the main events stream
            consumer_group="task-notifications",
            consumer_name="notifier-1",
        )
        self.telegram_client = telegram_client
        self.notification_chat_id = notification_chat_id

    def process_message(self, message_id: str, data: Dict[str, Any]) -> None:
        """Process a task event and send appropriate notification."""
        try:
            # Extract event type and data
            event_type = data.get("event_type", "")
            event_data = data.get("data", {})

            # Parse event data if it's a string
            if isinstance(event_data, str):
                event_data = json.loads(event_data)

            logger.info(f"Processing event {event_type} from message {message_id}")

            # Handle different event types
            if event_type == "TaskCreatedEvent":
                self._handle_task_created(event_data)
            elif event_type == "TaskCompletedEvent":
                self._handle_task_completed(event_data)
            elif event_type == "TaskAssignedEvent":
                self._handle_task_assigned(event_data)
            elif event_type == "TaskCancelledEvent":
                self._handle_task_cancelled(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            raise

    def _handle_task_created(self, event_data: Dict[str, Any]) -> None:
        """Handle task created event."""
        task_data = event_data.get("data", {})
        task_id = task_data.get("task_id")
        title = task_data.get("title")
        priority = task_data.get("priority")
        assigned_to = task_data.get("assigned_to")

        message = f"🆕 <b>New Task Created</b>\n\n"
        message += f"📋 Title: {title}\n"
        message += f"🔖 ID: <code>{task_id}</code>\n"
        message += f"⚡ Priority: {priority}\n"

        if assigned_to:
            message += f"👤 Assigned to: {assigned_to}\n"

        self.telegram_client.send_message(self.notification_chat_id, message)
        logger.info(f"Sent notification for task created: {task_id}")

    def _handle_task_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle task completed event."""
        task_data = event_data.get("data", {})
        task_id = task_data.get("task_id")
        completed_by = task_data.get("completed_by")

        message = f"✅ <b>Task Completed</b>\n\n"
        message += f"🔖 ID: <code>{task_id}</code>\n"

        if completed_by:
            message += f"👤 Completed by: {completed_by}\n"

        self.telegram_client.send_message(self.notification_chat_id, message)
        logger.info(f"Sent notification for task completed: {task_id}")

    def _handle_task_assigned(self, event_data: Dict[str, Any]) -> None:
        """Handle task assigned event."""
        task_data = event_data.get("data", {})
        task_id = task_data.get("task_id")
        assigned_to = task_data.get("assigned_to")
        assigned_by = task_data.get("assigned_by")

        message = f"👥 <b>Task Assigned</b>\n\n"
        message += f"🔖 ID: <code>{task_id}</code>\n"
        message += f"👤 Assigned to: {assigned_to}\n"

        if assigned_by:
            message += f"📝 Assigned by: {assigned_by}\n"

        self.telegram_client.send_message(self.notification_chat_id, message)
        logger.info(f"Sent notification for task assigned: {task_id}")

    def _handle_task_cancelled(self, event_data: Dict[str, Any]) -> None:
        """Handle task cancelled event."""
        task_data = event_data.get("data", {})
        task_id = task_data.get("task_id")
        cancelled_by = task_data.get("cancelled_by")
        reason = task_data.get("reason")

        message = f"❌ <b>Task Cancelled</b>\n\n"
        message += f"🔖 ID: <code>{task_id}</code>\n"

        if cancelled_by:
            message += f"👤 Cancelled by: {cancelled_by}\n"

        if reason:
            message += f"📝 Reason: {reason}\n"

        self.telegram_client.send_message(self.notification_chat_id, message)
        logger.info(f"Sent notification for task cancelled: {task_id}")
