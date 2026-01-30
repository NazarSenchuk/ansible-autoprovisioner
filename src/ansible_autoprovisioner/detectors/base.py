from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
@dataclass(frozen=True)
class DetectedInstance:
    instance_id: str
    ip_address: str
    detector: str
    tags: Dict[str, str]
class BaseDetector(ABC):
    @abstractmethod
    def detect(self) -> List[DetectedInstance]:
        pass
