import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class InstanceStatus(str, Enum):
    NEW = "new"
    PROVISIONING = "provisioning"
    PROVISIONED = "provisioned"
    PARTIAL = "partial_failure"
    FAILED = "failed"
    RETRYING = "retrying"
    ORPHANED = "orphaned"


class PlaybookStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class PlaybookResult:
    name: str
    file: str
    status: PlaybookStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    log_file: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    output: Optional[str] = None


@dataclass
class InstanceState:
    instance_id: str
    ip_address: str   
    groups: List[str] = None  
    tags: Dict[str, str] = None 
    detected_at: datetime = None
    last_seen_at: datetime = None 
    updated_at: datetime = None    
    playbooks: List[str] = None
    playbook_results: Dict[str, PlaybookResult] = None
    overall_status: InstanceStatus = InstanceStatus.NEW
    current_playbook: Optional[str] = None 
    
    last_attempt_at: Optional[datetime] = None    

    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.tags is None:
            self.tags = {}
        if self.playbooks is None:
            self.playbooks = []
        if self.playbook_results is None:
            self.playbook_results = {}

        if self.detected_at is None:
            self.detected_at = datetime.utcnow()
        if self.last_seen_at is None:
            self.last_seen_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
   
        
    


class StateManager:
    def __init__(self, state_file: str = "state.json"):
        self.state_file = state_file
        self._lock = threading.RLock()
        self._instances: Dict[str, InstanceState] = {}

        self.load_state()


    def load_state(self):
        with self._lock:
            if not os.path.exists(self.state_file):
                self._instances = {}
                return

            with open(self.state_file, "r") as f:
                raw = json.load(f)

            self._instances = {
                iid: self._deserialize_instance(data)
                for iid, data in raw.items()
            }

    def save_state(self):
        with self._lock:
            tmp_file = self.state_file + ".tmp"

            with open(tmp_file, "w") as f:
                json.dump(
                    {iid: self._serialize_instance(inst)
                     for iid, inst in self._instances.items()},
                    f,
                    indent=2,
                    default=str,
                )

            os.replace(tmp_file, self.state_file)

    def detect_instance(self, instance_id: str, ip: str, groups=None, tags=None,playbooks=None):
        with self._lock:
            inst = self._instances.get(instance_id)

            if inst:
                inst.last_seen_at = datetime.utcnow()
                inst.updated_at = datetime.utcnow()
            else:
                inst = InstanceState(
                    instance_id=instance_id,
                    ip_address=ip,
                    groups=groups or [],
                    tags=tags or {},
                    playbooks=playbooks or [],
                    overall_status=InstanceStatus.NEW,
                )
                self._instances[instance_id] = inst

            self.save_state()
            return inst

    def mark_provisioning(self, instance_id: str):
        with self._lock:
            inst = self._instances[instance_id]
            inst.overall_status = InstanceStatus.PROVISIONING
            inst.last_attempt_at = datetime.utcnow()
            inst.updated_at = datetime.utcnow()
            self.save_state()

    def mark_final_status(self, instance_id: str, status: InstanceStatus):
        with self._lock:
            inst = self._instances[instance_id]
            inst.overall_status = status
            inst.updated_at = datetime.utcnow()
            self.save_state()

    def start_playbook(self, instance_id: str, name: str, file: str):
        with self._lock:
            inst = self._instances[instance_id]
            now = datetime.utcnow()

            result = inst.playbook_results.get(name)

            if result is None:
                result = PlaybookResult(
                    name=name,
                    file=file,
                    status=PlaybookStatus.RUNNING,
                    started_at=now,
                    retry_count=0,
                )
                inst.playbook_results[name] = result
            else:
                result.retry_count += 1
                result.status = PlaybookStatus.RUNNING
                result.started_at = now

            result.error = None
            inst.current_playbook = name
            inst.last_attempt_at = now
            inst.updated_at = now

            self.save_state()
            return result



    def finish_playbook(
        self,
        instance_id: str,
        result: PlaybookResult,
        status: PlaybookStatus,
        error: Optional[str] = None,
        output: Optional[str] = None,
    ):
        with self._lock:
            result.status = status
            result.completed_at = datetime.utcnow()
            result.duration_sec = (
                result.completed_at - result.started_at
            ).total_seconds()
            result.error = error
            result.output = output
            inst = self._instances[instance_id]
            inst.current_playbook = None
            inst.updated_at = datetime.utcnow()

            self.save_state()


    def get_instances(self, status=None):
        instances = list(self._instances.values())

        if status is None:
            return instances

        return [i for i in instances if i.overall_status == status]

    def mark_all_provisioning_failed(self,):
        for inst in self.get_instances(status=InstanceStatus.PROVISIONING):
            self.mark_final_status(
                inst.instance_id,
                InstanceStatus.FAILED,
            )


    def _serialize_instance(self, inst: InstanceState) -> Dict[str, Any]:
        data = asdict(inst)
        data["overall_status"] = inst.overall_status.value
        data["playbook_results"] = {
            name: {
                **asdict(result),
                "status": result.status.value,
            }
            for name, result in inst.playbook_results.items()
        }
        return data


    def _deserialize_instance(self, data: Dict[str, Any]) -> InstanceState:
        data["overall_status"] = InstanceStatus(data["overall_status"])

        playbook_results = {}
        for name, r in data.get("playbook_results", {}).items():
            playbook_results[name] = PlaybookResult(
                **{**r, "status": PlaybookStatus(r["status"])}
            )

        data["playbook_results"] = playbook_results
        return InstanceState(**data)

    
_all__ = [
    'InstanceStatus',
    'PlaybookStatus',
    'PlaybookResult',
    'InstanceState',
    'StateManager'
]