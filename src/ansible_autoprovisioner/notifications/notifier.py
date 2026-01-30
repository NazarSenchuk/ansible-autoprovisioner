import logging
from .registry import NotifierRegistry

# Import notifiers to register them
from . import slack, telegram

logger = logging.getLogger(__name__)

class NotifierManager:
    def __init__(self, configs):
        self.notifiers = []
        for cfg in configs:
            try:
                name = cfg.get("name")
                options = cfg.get("options", {})
                self.notifiers.append(NotifierRegistry.create(name, **options))
            except Exception:
                logger.exception(f"Failed to initialize notifier: {cfg.get('name')}")

    def notify_all(self, instance_id: str, status: str, details: str = None):
        for n in self.notifiers:
            try:
                n.notify(instance_id, status, details)
            except Exception:
                logger.exception("Notification failed")
