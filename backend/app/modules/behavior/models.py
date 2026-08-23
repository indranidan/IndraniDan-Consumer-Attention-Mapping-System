"""
Module 6 — Consumer Behavior Backend Models
=============================================
Re-exports AI engine data models for backend service layer use.
"""

# Import directly from the AI engine models for single source of truth
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.behavior_analysis.models import (
    ShopperArchetype,
    BehaviorFeatureVector,
    ShopperClassification,
    Module6Summary,
)
from ai.behavior_analysis.config import BehaviorConfig

__all__ = [
    "ShopperArchetype",
    "BehaviorFeatureVector",
    "ShopperClassification",
    "Module6Summary",
    "BehaviorConfig",
]
