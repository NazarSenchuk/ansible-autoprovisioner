import logging
import os

from . import slack, telegram 
from .registry import NotifierRegistry

logger = logging.getLogger(__name__)


class NotifierManager:
    def __init__(self, configs, log_dir: str = None):
        self.notifiers = []
        self.log_dir = log_dir

        SYSTEM_OPTS = {"notify_on", "log_lines"}

        for cfg in configs:
            try:
                name = cfg.name
                options = cfg.options or {}

                notify_all_statuses = [
                    "success", "partial_failure", "failed"
                ]
                notify_on = options.get("notify_on", notify_all_statuses)
                log_lines = int(options.get("log_lines", 0))

                init_options = {
                    k: v for k, v in options.items() if k not in SYSTEM_OPTS
                }

                instance = NotifierRegistry.create(name, **init_options)
                self.notifiers.append({
                    "instance": instance,
                    "name": name,
                    "notify_on": notify_on,
                    "log_lines": log_lines
                })
            except Exception:
                logger.exception(
                    f"Failed to initialize notifier: {getattr(cfg, 'name', 'unknown')}"
                )

    def notify_all(self, instance, status: str, details: str = None) -> int:
        instance_id = instance.instance_id
        sent_count = 0
        for n in self.notifiers:
            try:
                if status not in n["notify_on"]:
                    logger.debug(f"Notifier {n['name']} skipped status {status}")
                    continue

                msg_details = details

                if (n["log_lines"] > 0 and
                        status in ("partial_failure", "failed") and
                        self.log_dir):
                    logs = self._get_last_logs(instance, n["log_lines"])
                    if logs:
                        if msg_details:
                            msg_details += f"\n\nLast logs:\n{logs}"
                        else:
                            msg_details = f"Last logs:\n{logs}"

                n["instance"].notify(instance_id, status, msg_details)
                sent_count += 1
            except Exception:
                logger.exception(f"Notification failed for notifier {n['name']}")

        return sent_count

    def _get_last_logs(self, instance, count) -> str:
        try:
            failed = [
                r for r in instance.playbook_results.values()
                if r.status == "error" and r.log_file
            ]
            if not failed:
                return None

            failed.sort(key=lambda r: r.completed_at or r.started_at, reverse=True)
            last_failed = failed[0]

            log_path = os.path.join(self.log_dir, last_failed.log_file)
            if not os.path.exists(log_path):
                return None

            with open(log_path, 'r') as f:
                lines = f.readlines()
                snippet = "".join(lines[-count:])
                return snippet.strip()
        except Exception as e:
            logger.error(f"Error reading logs for {instance.instance_id}: {e}")
            return None
