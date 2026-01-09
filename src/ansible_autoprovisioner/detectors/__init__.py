# src/ansible_autoprovisioner/detectors/__init__.py
"""
Detectors package for discovering instances from various sources.
"""

from .base import BaseDetector, DetectedInstance
from .static import StaticDetector
from .manager import DetectorManager

__all__ = [
    'BaseDetector',
    'DetectedInstance',
    'StaticDetector',
    'DetectorManager'
]