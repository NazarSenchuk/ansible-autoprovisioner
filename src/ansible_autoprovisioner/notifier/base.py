from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class BaseDetector(ABC):
    
    @abstractmethod
    def notify(self) :
        """Notify selected channels"""
        pass