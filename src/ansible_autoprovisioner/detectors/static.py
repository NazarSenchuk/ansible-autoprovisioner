from typing import List
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

from .base import BaseDetector, DetectedInstance


class StaticDetector(BaseDetector):
    def __init__(self, inventory_path = "inventory.ini" ):
        self.inventory_path = inventory_path

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
                    groups=[],
                    vars={}
                )

            inst = instances[instance_id]
            inst.groups.extend(g.name for g in host.groups if g.name != "all")
            inst.vars.update(host.vars)

        return list(instances.values())
