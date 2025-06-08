"""Telegram client wrapper for sending messages."""
import logging
from typing import Any, Dict, Optional

import requests

from app.config import Settings

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for interacting with Telegram Bot API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def send_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: Optional[str] = "HTML",
        disable_notification: bool = False,
    ) -> Dict[str, Any]:
        """Send a message to a Telegram chat."""
        logger.info(f"Sending message to chat {chat_id}")

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if not result.get("ok"):
                error_msg = result.get("description", "Unknown error")
                raise Exception(f"Telegram API error: {error_msg}")

            logger.info(f"Message sent successfully to chat {chat_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")
            raise

    def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = "HTML",
    ) -> Dict[str, Any]:
        """Send a photo to a Telegram chat."""
        logger.info(f"Sending photo to chat {chat_id}")

        url = f"{self.base_url}/sendPhoto"
        payload = {"chat_id": chat_id, "photo": photo_url}

        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = parse_mode

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if not result.get("ok"):
                error_msg = result.get("description", "Unknown error")
                raise Exception(f"Telegram API error: {error_msg}")

            logger.info(f"Photo sent successfully to chat {chat_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send photo to chat {chat_id}: {e}")
            raise

    def get_updates(self, offset: Optional[int] = None) -> Dict[str, Any]:
        """Get updates from Telegram (for webhook alternative)."""
        url = f"{self.base_url}/getUpdates"
        params = {}
        if offset:
            params["offset"] = offset

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()
            if not result.get("ok"):
                error_msg = result.get("description", "Unknown error")
                raise Exception(f"Telegram API error: {error_msg}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get updates: {e}")
            raise

    def check_health(self) -> bool:
        """Check if Telegram bot token is valid."""
        try:
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()

            result = response.json()
            return result.get("ok", False)

        except Exception as e:
            logger.error(f"Telegram health check failed: {e}")
            return False

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
