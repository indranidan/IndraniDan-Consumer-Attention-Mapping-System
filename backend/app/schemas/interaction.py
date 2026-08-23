"""
Module 5 — Product Interaction Analysis Schemas
=================================================
Pydantic schemas for Module 5 endpoints:
- Product engagement metrics
- Shelf interaction monitoring
- Multi-product comparison patterns
- Granular interaction events
- Overall summary & reports
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class ProductEngagementItem(BaseModel):
    """Product engagement metrics item."""
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


class ShelfInteractionItem(BaseModel):
    """Shelf interaction monitoring item."""
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


class ProductComparisonItem(BaseModel):
    """Observed multi-product comparison sequence item."""
    pattern_id: str
    session_id: Optional[str] = None
    track_id: int
    product_ids: List[str] = []
    product_names: List[str] = []
    interaction_sequence: List[Dict[str, Any]] = []
    total_duration_sec: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    pattern_description: str


class InteractionEventItem(BaseModel):
    """Granular product interaction event record."""
    event_id: str
    event_type: str
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
    source: str = "MODULE_4_ATTENTION"
    metadata: Optional[Dict[str, Any]] = None


class Module5SummarySchema(BaseModel):
    """Overview summary for Module 5."""
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
    config_hash: Optional[str] = None
    analyzed_at: Optional[str] = None
    disclaimer: str = (
        "Module 5 analyzes consumer-product interactions building on Module 3 tracking "
        "and Module 4 attention data. Product pickup/return detection is verified only when "
        "sufficient visual evidence exists. Purchase events require POS transaction integration."
    )


class Module5AnalysisResponse(BaseModel):
    """Full Module 5 analysis results response."""
    job_id: uuid.UUID
    camera_id: uuid.UUID
    store_id: uuid.UUID
    status: str = "COMPLETED"
    summary: Module5SummarySchema
    products: List[ProductEngagementItem] = []
    shelves: List[ShelfInteractionItem] = []
    comparisons: List[ProductComparisonItem] = []
    total_event_count: int = 0
    disclaimer: str = (
        "Module 5 analyzes consumer-product interactions building on Module 3 tracking "
        "and Module 4 attention data. No fictitious pickups or purchases are fabricated."
    )


class Module5ReportResponse(BaseModel):
    """Structured report data response."""
    job_id: uuid.UUID
    json_report: Dict[str, Any]
    markdown_report: str
