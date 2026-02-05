import logging
from pathlib import Path
from typing import List

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import init_plugin_loader

from .base import BaseDetector, DetectedInstance

init_plugin_loader([])
logger = logging.getLogger(__name__)


class StaticDetector(BaseDetector):
    def __init__(self, inventory: str = "inventory.ini"):
        self.inventory_path = inventory
        logger.info("Initializing Static Detector")
        if not Path(inventory).exists():
            raise RuntimeError(f"Inventory file not found: {inventory}")

    def detect(self) -> List[DetectedInstance]:
        loader = DataLoader()
        inventory = InventoryManager(loader=loader, sources=[self.inventory_path])
        instances = {}
        for host in inventory.hosts.values():
            ip = host.vars.get("ansible_host", host.name)
            instance_id = f"static-{ip}"
            if instance_id not in instances:
                instances[instance_id] = DetectedInstance(
                    instance_id=instance_id,
                    ip_address=ip,
                    detector="static",
                    tags={}
                )
            inst = instances[instance_id]
            inst.tags.update(host.vars)
        return list(instances.values())
