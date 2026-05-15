import logging
from plyer import notification
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

class AlertSystem:
    def __init__(self, desktop_notify: bool = True, telegram_token: str = None, telegram_chat_id: str = None):
        self.desktop_notify = desktop_notify
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_bot = None
        if telegram_token and TELEGRAM_AVAILABLE:
            try:
                self.telegram_bot = Bot(token=telegram_token)
            except Exception as e:
                logger.error(f"Telegram bot init failed: {e}")

    def send(self, title: str, message: str, severity: str = "warning"):
        # Desktop notification
        if self.desktop_notify:
            try:
                notification.notify(
                    title=f"SPY-IMSICD: {title}",
                    message=message,
                    timeout=10
                )
            except Exception as e:
                logger.debug(f"Desktop notify failed: {e}")

        # Telegram
        if self.telegram_bot and self.telegram_chat_id:
            try:
                full_msg = f"*{title}*\n{message}"
                self.telegram_bot.send_message(chat_id=self.telegram_chat_id, text=full_msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")

        # Also log
        logger.warning(f"ALERT: {title} - {message}")
