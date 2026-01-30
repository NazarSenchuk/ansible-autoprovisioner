import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..state import StateManager, InstanceStatus
from ..config import DaemonConfig

logger = logging.getLogger(__name__)

class ApiInterface:
    def __init__(self, state: StateManager, config: DaemonConfig):
        self.state = state
        self.config = config

    def get_config(self) -> Dict[str, Any]:
        return {
            "rules_count": len(self.config.rules),
            "interval": self.config.interval,
            "state_file": self.config.state_file,
            "log_dir": self.config.log_dir,
            "max_retries": self.config.max_retries,
            "ui": self.config.ui,
            "detectors": [
                {"name": d.name, "options": d.options}
                for d in self.config.detectors
            ],
        }

    def get_logs(self, instance_id: str, playbook: Optional[str] = None) -> Dict[str, Any]:
        log_dir = Path(self.config.log_dir) / instance_id
        if not log_dir.exists():
            return {"success": False, "error": "No logs for instance"}
        if playbook is None:
            logs = sorted([p.name for p in log_dir.iterdir() if p.is_file() and p.suffix == ".log"])
            return {"success": True, "instance": instance_id, "logs": logs}
        log_file = log_dir / playbook
        if not log_file.exists():
            return {"success": False, "error": "Log not found"}
        content = log_file.read_text(errors="ignore")
        return {"success": True, "instance": instance_id, "playbook": playbook, "content": content}

    def add_instance(
        self,
        instance_id: str,
        ip_address: str,
        groups: List[str] = None,
        tags: Dict[str, Any] = None,
        playbooks: List[str] = None,
    ) -> Dict[str, Any]:
        try:
            if not instance_id or not ip_address:
                return {"success": False, "error": "Instance ID and IP address are required"}
            existing = self.state.get_instance(instance_id)
            if existing:
                return {"success": False, "error": f"Instance {instance_id} already exists"}
            self.state.detect_instance(
                instance_id=instance_id,
                ip=ip_address,
                groups=groups or [],
                tags=tags or {},
                playbook_tasks=playbooks or [],
            )
            logger.info(f"Manually added instance: {instance_id}")
            return {"success": True, "instance_id": instance_id}
        except Exception as e:
            logger.error(f"Error adding instance {instance_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def retry_instance(self, instance_id: str) -> Dict[str, Any]:
        try:
            instance = self.state.get_instance(instance_id)
            if not instance:
                return {"success": False, "error": f"Instance {instance_id} not found"}
            if instance.overall_status not in [InstanceStatus.ERROR, InstanceStatus.SUCCESS]:
                return {
                    "success": False,
                    "error": f"Cannot retry instance with status: {instance.overall_status.value}",
                }
            self.state.mark_final_status(instance_id, InstanceStatus.PENDING)
            logger.info(f"Retry requested for instance: {instance_id}")
            return {"success": True, "instance_id": instance_id}
        except Exception as e:
            logger.error(f"Error retrying instance {instance_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_instance_details(self, instance_id: str) -> Dict[str, Any]:
        try:
            instance = self.state.get_instance(instance_id)
            if not instance:
                return {"success": False, "error": f"Instance {instance_id} not found"}
            return {"success": True, "instance": instance.to_dict()}
        except Exception as e:
            logger.error(f"Error getting details for instance {instance_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_instance(self, instance_id: str, force: bool = False) -> Dict[str, Any]:
        try:
            instance = self.state.get_instance(instance_id)
            if not instance:
                return {"success": False, "error": f"Instance {instance_id} not found"}
            if not force and instance.overall_status == InstanceStatus.RUNNING:
                return {
                    "success": False,
                    "error": f"Instance {instance_id} is currently running. Use force=true to delete anyway.",
                }
            self.state.delete_instance(instance_id)
            logger.info(f"Deleted instance: {instance_id}")
            return {"success": True, "instance_id": instance_id}
        except Exception as e:
            logger.error(f"Error deleting instance {instance_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def list_instances(self, status: Optional[str] = None):
        return self.state.get_instances(status=status)

    def get_stats(self) -> Dict[str, Any]:
        instances = self.state.get_instances()
        status_counts = {s.value: 0 for s in InstanceStatus}
        for inst in instances:
            status_counts[inst.overall_status.value] += 1
        return {
            "total_instances": len(instances),
            "status_counts": status_counts,
            "successful": status_counts.get(InstanceStatus.SUCCESS.value, 0),
            "failed": status_counts.get(InstanceStatus.ERROR.value, 0),
            "running": status_counts.get(InstanceStatus.RUNNING.value, 0),
            "pending": status_counts.get(InstanceStatus.PENDING.value, 0),
            "orphaned": status_counts.get(InstanceStatus.ORPHANED.value, 0),
        }
