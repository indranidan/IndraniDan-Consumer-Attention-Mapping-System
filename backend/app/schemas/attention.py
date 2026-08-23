"""
Module 4 — Attention Analysis Schemas
=======================================
Pydantic response models for Module 4 Attention Engine endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class ShelfMetricItem(BaseModel):
    """Shelf engagement metric item."""

    shelf_id: str
    shelf_name: str
    store_id: Optional[str] = None
    camera_id: Optional[str] = None
    visitors: int = 0
    viewers: int = 0
    dwell_time_sec: float = 0.0
    shelf_attention_time_sec: float = 0.0
    average_shelf_attention_sec: float = 0.0
    attention_event_count: int = 0
    repeated_attention_events: int = 0
    score: float = 0.0


class ProductMetricItem(BaseModel):
    """Product focus metric item."""

    product_id: str
    product_name: str
    sku: Optional[str] = None
    shelf_id: Optional[str] = None
    shelf_name: Optional[str] = None
    is_configured: bool = False
    viewers: int = 0
    attention_events: int = 0
    total_focus_duration_sec: float = 0.0
    average_focus_duration_sec: float = 0.0
    repeated_attention_events: int = 0
    status_note: str = "Unavailable / Not Configured"


class AttentionEventItem(BaseModel):
    """Granular attention event record."""

    event_id: str
    track_id: int
    session_id: Optional[str] = None
    camera_id: Optional[str] = None
    store_id: Optional[str] = None
    timestamp: float
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    attention_type: str
    target_type: str
    target_id: str
    target_name: str
    zone_id: str
    attention_direction: str
    confidence: float
    status: str
    visit_number: int
    start_frame: int = 0
    end_frame: Optional[int] = None
    gaze_origin: Optional[List[int]] = None
    gaze_direction: Optional[List[float]] = None


class Module4QualityMetrics(BaseModel):
    """Quality and detection confidence stats."""

    total_frames_analyzed: int = 0
    total_face_crops_attempted: int = 0
    valid_face_detections: int = 0
    low_confidence_faces: int = 0
    occluded_or_missing_faces: int = 0
    face_detection_rate: float = 0.0
    average_pose_confidence: float = 0.0


class Module4SummarySchema(BaseModel):
    """Summary overview for Module 4."""

    total_attention_events: int = 0
    total_attention_duration_sec: float = 0.0
    average_attention_duration_sec: float = 0.0
    total_dwell_time_sec: float = 0.0
    total_shelf_attention_time_sec: float = 0.0
    total_product_focus_duration_sec: float = 0.0
    total_repeated_attention_events: int = 0
    total_unique_viewers: int = 0
    most_attended_shelf: Optional[Dict[str, Any]] = None
    shelf_engagement_score_avg: float = 0.0
    product_mapping_configured: bool = False
    config_hash: Optional[str] = None
    analyzed_at: Optional[str] = None
    disclaimer: str = (
        "All attention metrics are ESTIMATED based on 3D head pose and orientation "
        "relative to configured regions. The system does not perform pixel-level eye gaze tracking."
    )


class Module4AnalysisResponse(BaseModel):
    """Full Module 4 analysis results for an AI job."""

    job_id: uuid.UUID
    camera_id: uuid.UUID
    store_id: uuid.UUID
    status: str = "COMPLETED"
    summary: Module4SummarySchema
    shelves: List[ShelfMetricItem] = []
    products: List[ProductMetricItem] = []
    quality_metrics: Optional[Module4QualityMetrics] = None
    heatmap: Optional[Dict[str, Any]] = None
    disclaimer: str = (
        "All attention metrics are ESTIMATED based on head orientation and geometric projection. "
        "Pixel-level eye gaze tracking is not performed."
    )


class Module4ReportResponse(BaseModel):
    """Structured report data response."""

    job_id: uuid.UUID
    json_report: Dict[str, Any]
    markdown_report: str


class Module4HeatmapResponse(BaseModel):
    """Heatmap metadata and spatial density coordinates."""

    job_id: uuid.UUID
    camera_width: int
    camera_height: int
    total_points: int
    points: List[Dict[str, Any]]
    image_url: Optional[str] = None
