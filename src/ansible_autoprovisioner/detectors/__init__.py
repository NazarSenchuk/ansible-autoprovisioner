from .base import BaseDetector, DetectedInstance
from .manager import DetectorManager
from .registry import DetectorRegistry
from .static import StaticDetector
from .aws import AWSDetector
DetectorRegistry.register("static", StaticDetector)
DetectorRegistry.register("aws", AWSDetector)
__all__ = [
    "BaseDetector",
    "DetectedInstance",
    "DetectorManager",
    "DetectorRegistry",
]
