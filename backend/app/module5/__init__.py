"""
Module 5 — Product Interaction Analysis Module
===============================================
Master package for Module 5:
- Product Pickup Detection (Visual evidence gated)
- Product Return Detection (Prior pickup validated)
- Shelf Interaction Monitoring
- Product Engagement Matrix
- Observed Multi-Product Comparisons & Consideration Journeys
- Event Deduplication & ByteTrack ID Preservation
"""

from app.module5.engine import Module5InteractionEngine
from app.module5.models import (
    InteractionEventType,
    InteractionSource,
    Module5Summary,
    ProductComparisonPattern,
    ProductEngagementMetric,
    ProductInteractionEvent,
    ShelfInteractionMetric,
)
from app.module5.report_generator import Module5ReportGenerator

__all__ = [
    "Module5InteractionEngine",
    "Module5ReportGenerator",
    "InteractionEventType",
    "InteractionSource",
    "ProductInteractionEvent",
    "ProductEngagementMetric",
    "ShelfInteractionMetric",
    "ProductComparisonPattern",
    "Module5Summary",
]
