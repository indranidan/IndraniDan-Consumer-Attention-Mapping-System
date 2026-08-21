"""
Module 5 — Product Interaction Analysis Data Models
=====================================================
Domain data structures and enumerations for Module 5:
- Interaction Event Types (VIEWED, PICKED_UP, RETURNED, PURCHASED, COMPARED)
- Product Engagement Metrics
- Shelf Interaction Metrics
- Product Comparison Patterns
- Summary Aggregation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InteractionEventType(str, Enum):
    """Supported product interaction event types."""
    PRODUCT_VIEWED = "PRODUCT_VIEWED"
    PRODUCT_PICKED_UP = "PRODUCT_PICKED_UP"
    PRODUCT_RETURNED = "PRODUCT_RETURNED"
    PRODUCT_PURCHASED = "PRODUCT_PURCHASED"
    PRODUCT_COMPARED = "PRODUCT_COMPARED"


class InteractionSource(str, Enum):
    """Source that generated the interaction event."""
    MODULE_4_ATTENTION = "MODULE_4_ATTENTION"
    SPATIAL_INTERACTION = "SPATIAL_INTERACTION"
    HAND_INTERACTION = "HAND_INTERACTION"
    POS_TRANSACTION = "POS_TRANSACTION"
    BEHAVIORAL_HEURISTIC = "BEHAVIORAL_HEURISTIC"


@dataclass
class ProductInteractionEvent:
    """A granular product or shelf interaction event."""
    event_id: str
    event_type: InteractionEventType
    track_id: int
    session_id: Optional[str] = None
    store_id: Optional[str] = None
    camera_id: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    sku: Optional[str] = None
    shelf_id: Optional[str] = None
    shelf_name: Optional[str] = None
    timestamp: float = 0.0
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration_seconds: float = 0.0
    confidence: float = 0.0
    source: InteractionSource = InteractionSource.MODULE_4_ATTENTION
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, InteractionEventType) else str(self.event_type),
            "track_id": self.track_id,
            "session_id": self.session_id,
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "product_id": self.product_id,
            "product_name": self.product_name or "Unknown Product",
            "sku": self.sku,
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name or "Unknown Shelf",
            "timestamp": round(self.timestamp, 3),
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3) if self.end_time is not None else None,
            "duration_seconds": round(self.duration_seconds, 3),
            "confidence": round(self.confidence, 4),
            "source": self.source.value if isinstance(self.source, InteractionSource) else str(self.source),
            "metadata": self.metadata,
        }


@dataclass
class ProductEngagementMetric:
    """Engagement metrics for a specific product."""
    product_id: str
    product_name: str
    sku: Optional[str] = None
    shelf_id: Optional[str] = None
    shelf_name: Optional[str] = None
    is_spatial_mapped: bool = False
    views: int = 0
    unique_viewers: int = 0
    total_view_duration_sec: float = 0.0
    average_view_duration_sec: float = 0.0
    pickup_events: int = 0
    return_events: int = 0
    comparison_events: int = 0
    repeat_interactions: int = 0
    purchase_count: int = 0
    status_note: str = "Active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "sku": self.sku,
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name,
            "is_spatial_mapped": self.is_spatial_mapped,
            "views": self.views,
            "unique_viewers": self.unique_viewers,
            "total_view_duration_sec": round(self.total_view_duration_sec, 2),
            "average_view_duration_sec": round(self.average_view_duration_sec, 2),
            "pickup_events": self.pickup_events,
            "return_events": self.return_events,
            "comparison_events": self.comparison_events,
            "repeat_interactions": self.repeat_interactions,
            "purchase_count": self.purchase_count,
            "status_note": self.status_note,
        }


@dataclass
class ShelfInteractionMetric:
    """
    Interaction metrics for a physical shelf.
    Distinguishes:
    - Shelf Visit (shopper in zone)
    - Shelf Attention (head pose / gaze at shelf)
    - Shelf Interaction (dwell + proximity + attention at shelf)
    - Pickups & Returns
    - Engagement Duration
    """
    shelf_id: str
    shelf_name: str
    shelf_code: Optional[str] = None
    zone_id: Optional[str] = None
    shelf_visits: int = 0
    shelf_viewers: int = 0
    shelf_attention_events: int = 0
    shelf_attention_duration_sec: float = 0.0
    product_views: int = 0
    shelf_interactions: int = 0
    pickup_events: int = 0
    return_events: int = 0
    total_engagement_duration_sec: float = 0.0
    average_engagement_duration_sec: float = 0.0
    associated_products_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name,
            "shelf_code": self.shelf_code,
            "zone_id": self.zone_id,
            "shelf_visits": self.shelf_visits,
            "shelf_viewers": self.shelf_viewers,
            "shelf_attention_events": self.shelf_attention_events,
            "shelf_attention_duration_sec": round(self.shelf_attention_duration_sec, 2),
            "product_views": self.product_views,
            "shelf_interactions": self.shelf_interactions,
            "pickup_events": self.pickup_events,
            "return_events": self.return_events,
            "total_engagement_duration_sec": round(self.total_engagement_duration_sec, 2),
            "average_engagement_duration_sec": round(self.average_engagement_duration_sec, 2),
            "associated_products_count": self.associated_products_count,
        }


@dataclass
class ProductComparisonPattern:
    """
    Record of an observed multi-product consideration sequence by a single shopper.
    """
    pattern_id: str
    session_id: Optional[str]
    track_id: int
    product_ids: List[str]
    product_names: List[str]
    interaction_sequence: List[Dict[str, Any]]
    total_duration_sec: float
    start_time: float
    end_time: float
    pattern_description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "session_id": self.session_id,
            "track_id": self.track_id,
            "product_ids": self.product_ids,
            "product_names": self.product_names,
            "interaction_sequence": self.interaction_sequence,
            "total_duration_sec": round(self.total_duration_sec, 2),
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "pattern_description": self.pattern_description,
        }


@dataclass
class Module5Summary:
    """Overall summary statistics for Module 5 analysis."""
    total_views: int = 0
    total_unique_viewers: int = 0
    total_view_duration_sec: float = 0.0
    average_view_duration_sec: float = 0.0
    total_pickups: int = 0
    total_returns: int = 0
    total_comparisons: int = 0
    total_purchases: int = 0
    total_shelf_interactions: int = 0
    total_engagement_duration_sec: float = 0.0
    pickup_detection_status: str = "INSUFFICIENT_VISUAL_EVIDENCE"
    purchase_data_status: str = "UNAVAILABLE / NOT CONFIGURED (No POS Data)"
    product_mapping_configured: bool = False
    disclaimer: str = (
        "Module 5 analyzes consumer-product interactions building on Module 3 tracking "
        "and Module 4 attention data. Product pickup/return detection is verified only when "
        "sufficient visual evidence exists. Purchase events require POS transaction integration."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_views": self.total_views,
            "total_unique_viewers": self.total_unique_viewers,
            "total_view_duration_sec": round(self.total_view_duration_sec, 2),
            "average_view_duration_sec": round(self.average_view_duration_sec, 2),
            "total_pickups": self.total_pickups,
            "total_returns": self.total_returns,
            "total_comparisons": self.total_comparisons,
            "total_purchases": self.total_purchases,
            "total_shelf_interactions": self.total_shelf_interactions,
            "total_engagement_duration_sec": round(self.total_engagement_duration_sec, 2),
            "pickup_detection_status": self.pickup_detection_status,
            "purchase_data_status": self.purchase_data_status,
            "product_mapping_configured": self.product_mapping_configured,
            "disclaimer": self.disclaimer,
        }
