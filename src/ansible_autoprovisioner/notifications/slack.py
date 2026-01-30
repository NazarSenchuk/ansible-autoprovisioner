import requests
import logging
from .base import BaseNotifier
from .registry import NotifierRegistry

logger = logging.getLogger(__name__)

class SlackNotifier(BaseNotifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def notify(self, instance_id: str, status: str, details: str = None):
        try:
            emoji = "✅" if status == "success" else "❌"
            text = f"{emoji} *Instance {instance_id}* provisioned with status: *{status.upper()}*"
            if details:
                text += f"\n> {details}"
            
            payload = {"text": text}
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception:
            logger.exception("Slack notify fail")

NotifierRegistry.register("slack", SlackNotifier)
