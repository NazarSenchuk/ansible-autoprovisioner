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
    SKIPPED = "skipped"
    ORPHANED = "orphaned"


class PlaybookStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file": self.file,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_sec": self.duration_sec,
            "log_file": self.log_file,
            "error": self.error,
            "retry_count": self.retry_count,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaybookResult':
        return cls(
            name=data["name"],
            file=data["file"],
            status=PlaybookStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            duration_sec=data.get("duration_sec"),
            log_file=data.get("log_file"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            output=data.get("output"),
        )


@dataclass
class InstanceState:
    instance_id: str
    ip_address: str
    detector: str  = "static"
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
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "ip_address": self.ip_address,
            "detector" : self.detector
            "groups": self.groups,
            "tags": self.tags,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "playbooks": self.playbooks,
            "playbook_results": {
                name: result.to_dict()
                for name, result in self.playbook_results.items()
            },
            "overall_status": self.overall_status.value if self.overall_status else "unknown",
            "current_playbook": self.current_playbook,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstanceState':
        playbook_results = {
            name: PlaybookResult.from_dict(res_data)
            for name, res_data in data.get("playbook_results", {}).items()
        }
        
        instance = cls(
            instance_id=data["instance_id"],
            ip_address=data["ip_address"],
            detector=data["detector"],
            groups=data.get("groups", []),
            tags=data.get("tags", {}),
            playbooks=data.get("playbooks", []),
            overall_status=InstanceStatus(data.get("overall_status", InstanceStatus.NEW)),
            current_playbook=data.get("current_playbook"),
        )
        
        if data.get("detected_at"):
            instance.detected_at = datetime.fromisoformat(data["detected_at"])
        if data.get("last_seen_at"):
            instance.last_seen_at = datetime.fromisoformat(data["last_seen_at"])
        if data.get("updated_at"):
            instance.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_attempt_at"):
            instance.last_attempt_at = datetime.fromisoformat(data["last_attempt_at"])
            
        instance.playbook_results = playbook_results
        return instance
   
        
    


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
                iid: InstanceState.from_dict(data)
                for iid, data in raw.items()
            }

    def save_state(self):
        with self._lock:
            tmp_file = self.state_file + ".tmp"

            with open(tmp_file, "w") as f:
                json.dump(
                    {iid: inst.to_dict()
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
                inst.detected_at   =  datetime.utcnow()
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

            if inst.playbooks == []:
                inst.overall_status = InstanceStatus.SKIPPED 
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
            if status == InstanceStatus.NEW:
                for p in inst.playbook_results.values():
                    p.retry_count = 0
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

    def get_instance(self, instance_id: str) -> Optional[InstanceState]:
        return self._instances.get(instance_id)
                
    def delete_instance(self, instance_id: str) -> bool:
        with self._lock:
            if instance_id in self._instances:
                del self._instances[instance_id]
                self.save_state()
                return True
            return False
                    





    
_all__ = [
    'InstanceStatus',
    'PlaybookStatus',
    'PlaybookResult',
    'InstanceState',
    'StateManager'
]