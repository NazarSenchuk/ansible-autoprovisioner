import requests
import logging
from .base import BaseNotifier
from .registry import NotifierRegistry

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def notify(self, instance_id: str, status: str, details: str = None):
        try:
            emoji = "✅" if status == "success" else "❌"
            text = f"{emoji} *Instance {instance_id}* status: *{status.upper()}*"
            if details:
                text += f"\n`{details}`"
            
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload, timeout=5)
        except Exception:
            logger.exception("Telegram notify fail")

NotifierRegistry.register("telegram", TelegramNotifier)
