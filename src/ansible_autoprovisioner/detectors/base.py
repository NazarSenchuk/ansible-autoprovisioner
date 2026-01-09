# src/ansible_autoprovisioner/detectors/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass



@dataclass(frozen=True)
class DetectedInstance:
    instance_id: str
    ip_address: str
    groups: List[str]
    vars: Dict[str, str]

class BaseDetector(ABC):
    """Abstract base class for all instance detectors"""
    
    @abstractmethod
    def detect(self) -> List[DetectedInstance]:
        """Detect and return all instances from this source"""
        pass