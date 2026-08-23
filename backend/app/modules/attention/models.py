"""
Module 4 — Attention Analysis Models & Data Foundation
========================================================
Internal data structures and typed representations for Module 4.
All attention metrics are explicitly labeled as estimated head-pose-based
attention, never claiming pixel-level eye gaze tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid


class AttentionType(str, Enum):
    """Types of attention classified by the engine."""

    HEAD_POSE_ATTENTION = "HEAD_POSE_ATTENTION"
    SHELF_ATTENTION = "SHELF_ATTENTION"
    PRODUCT_ATTENTION = "PRODUCT_ATTENTION"
    UNKNOWN_ATTENTION = "UNKNOWN_ATTENTION"


class AttentionDirection(str, Enum):
    """Discrete attention direction derived from head pose."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class AttentionState(str, Enum):
    """Attention state."""

    ATTENDING = "ATTENDING"
    NOT_ATTENDING = "NOT_ATTENDING"
    UNKNOWN = "UNKNOWN"


@dataclass
class AttentionSubject:
    """
    Core representation of a tracked subject (shopper) for attention analysis.
    Preserves existing ByteTrack ID and spatial movement context from Module 3.
    """

    track_id: int
    session_id: Optional[str] = None
    camera_id: Optional[str] = None
    store_id: Optional[str] = None
    timestamp: float = 0.0
    frame_number: int = 0
    person_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    person_position: Tuple[int, int] = (0, 0)
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None


@dataclass
class HeadPoseData:
    """
    Estimated head orientation angles and landmark detection metadata.
    """

    yaw: float = 0.0          # Left (-)/Right (+) in degrees
    pitch: float = 0.0        # Down (-)/Up (+) in degrees
    roll: float = 0.0         # Head tilt in degrees
    face_detected: bool = False
    confidence: float = 0.0   # 0.0 to 1.0
    face_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    nose_point: Tuple[int, int] = (0, 0)
    status: str = "unavailable"  # "available", "unavailable", "low_confidence", "occluded"
    method: str = "head_orientation"  # Clearly labels estimation proxy


@dataclass
class GazeEstimate:
    """
    2D estimated viewing direction in camera image coordinates.
    Labeled as estimated attention / head-pose-based attention.
    """

    origin: Tuple[int, int] = (0, 0)          # [x, y] nose/face anchor point
    direction: Tuple[float, float] = (0.0, 0.0) # [dx, dy] normalized unit vector
    confidence: float = 0.0                   # 0.0 to 1.0
    method: str = "head_pose_based_attention"
    is_valid: bool = False


@dataclass
class AttentionEventRecord:
    """
    Structured record of a sustained attention event toward a shelf, product, or zone.
    Consecutive attention frames are grouped; look-aways create distinct events.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    track_id: int = 0
    session_id: Optional[str] = None
    camera_id: Optional[str] = None
    store_id: Optional[str] = None
    timestamp: float = 0.0
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    attention_type: str = AttentionType.HEAD_POSE_ATTENTION.value
    target_type: str = "unknown"              # "shelf", "product", "zone", "unknown"
    target_id: str = "unknown"
    target_name: str = "Unknown"
    zone_id: str = "unknown"
    attention_direction: str = AttentionDirection.UNKNOWN.value
    confidence: float = 0.0
    status: str = "active"                    # "active", "completed", "track_lost"
    visit_number: int = 1                     # Number of times this track visited this target
    start_frame: int = 0
    end_frame: Optional[int] = None
    gaze_origin: Optional[Tuple[int, int]] = None
    gaze_direction: Optional[Tuple[float, float]] = None

    def close(self, end_time: float, end_frame: int, status: str = "completed") -> None:
        """Finalize and close this attention event."""
        self.end_time = round(end_time, 3)
        self.end_frame = end_frame
        self.duration_seconds = round(max(0.0, end_time - self.start_time), 3)
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """Convert event record to dictionary."""
        return {
            "event_id": self.event_id,
            "track_id": self.track_id,
            "session_id": self.session_id,
            "camera_id": self.camera_id,
            "store_id": self.store_id,
            "timestamp": round(self.timestamp, 3),
            "start_time": round(self.start_time, 3),
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "attention_type": self.attention_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "zone_id": self.zone_id,
            "attention_direction": self.attention_direction,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "visit_number": self.visit_number,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "gaze_origin": list(self.gaze_origin) if self.gaze_origin else None,
            "gaze_direction": list(self.gaze_direction) if self.gaze_direction else None,
        }


@dataclass
class ShelfEngagement:
    """
    Engagement metrics for a specific configured shelf / shelf zone.
    """

    shelf_id: str
    shelf_name: str
    store_id: Optional[str] = None
    camera_id: Optional[str] = None
    visitors: int = 0                         # People physically observed in shelf zone
    viewers: int = 0                          # People who actually looked at shelf
    dwell_time_sec: float = 0.0               # Physical dwell time in zone
    shelf_attention_time_sec: float = 0.0     # Time gaze was directed at shelf
    average_shelf_attention_sec: float = 0.0  # Attention time / event count
    attention_event_count: int = 0
    repeated_attention_events: int = 0        # Events where visit_number > 1
    score: float = 0.0                        # Formula-derived shelf engagement score (0-100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name,
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "visitors": self.visitors,
            "viewers": self.viewers,
            "dwell_time_sec": round(self.dwell_time_sec, 2),
            "shelf_attention_time_sec": round(self.shelf_attention_time_sec, 2),
            "average_shelf_attention_sec": round(self.average_shelf_attention_sec, 2),
            "attention_event_count": self.attention_event_count,
            "repeated_attention_events": self.repeated_attention_events,
            "score": round(self.score, 1),
        }


@dataclass
class ProductAttention:
    """
    Attention metrics for a specific product.
    Only populated if spatial product mapping is configured; otherwise marked as not configured.
    """

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "sku": self.sku,
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name,
            "is_configured": self.is_configured,
            "viewers": self.viewers if self.is_configured else 0,
            "attention_events": self.attention_events if self.is_configured else 0,
            "total_focus_duration_sec": round(self.total_focus_duration_sec, 2) if self.is_configured else 0.0,
            "average_focus_duration_sec": round(self.average_focus_duration_sec, 2) if self.is_configured else 0.0,
            "repeated_attention_events": self.repeated_attention_events if self.is_configured else 0,
            "status_note": self.status_note,
        }


@dataclass
class AttentionQualityMetrics:
    """Detection quality and confidence breakdown."""

    total_frames_analyzed: int = 0
    total_face_crops_attempted: int = 0
    valid_face_detections: int = 0
    low_confidence_faces: int = 0
    occluded_or_missing_faces: int = 0
    face_detection_rate: float = 0.0
    average_pose_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_frames_analyzed": self.total_frames_analyzed,
            "total_face_crops_attempted": self.total_face_crops_attempted,
            "valid_face_detections": self.valid_face_detections,
            "low_confidence_faces": self.low_confidence_faces,
            "occluded_or_missing_faces": self.occluded_or_missing_faces,
            "face_detection_rate": round(self.face_detection_rate, 4),
            "average_pose_confidence": round(self.average_pose_confidence, 4),
        }


@dataclass
class Module4Summary:
    """Executive summary of Module 4 analysis results."""

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
    disclaimer: str = (
        "All attention metrics are ESTIMATED based on 3D head pose and orientation "
        "relative to configured regions. The system does not perform pixel-level eye gaze tracking."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_attention_events": self.total_attention_events,
            "total_attention_duration_sec": round(self.total_attention_duration_sec, 2),
            "average_attention_duration_sec": round(self.average_attention_duration_sec, 2),
            "total_dwell_time_sec": round(self.total_dwell_time_sec, 2),
            "total_shelf_attention_time_sec": round(self.total_shelf_attention_time_sec, 2),
            "total_product_focus_duration_sec": round(self.total_product_focus_duration_sec, 2),
            "total_repeated_attention_events": self.total_repeated_attention_events,
            "total_unique_viewers": self.total_unique_viewers,
            "most_attended_shelf": self.most_attended_shelf,
            "shelf_engagement_score_avg": round(self.shelf_engagement_score_avg, 1),
            "product_mapping_configured": self.product_mapping_configured,
            "disclaimer": self.disclaimer,
        }
