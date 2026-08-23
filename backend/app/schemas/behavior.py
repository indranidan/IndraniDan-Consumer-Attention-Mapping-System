"""
Module 6 — Consumer Behavior Analysis Schemas
================================================
Pydantic schemas for Module 6 REST API endpoints:
- Behavioral feature vectors
- Shopper archetype classifications
- Journey timelines
- Zone transition matrices
- Funnel metrics & friction points
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BehaviorFeatureVectorSchema(BaseModel):
    """Behavioral feature vector for a shopper session."""
    path_efficiency: float = 0.0
    dwell_to_transit_ratio: float = 0.0
    zone_breadth: int = 0
    gaze_alternation_rate: float = 0.0
    pickup_to_return_ratio: float = 0.0
    brand_concentration: float = 0.0
    promo_deviation_count: int = 0
    has_reduced_confidence: bool = False


class ShopperClassificationSchema(BaseModel):
    """Classification result for a shopper session."""
    track_id: int
    session_id: Optional[str] = None
    primary_segment: str
    confidence: float = 0.0
    secondary_segment: Optional[str] = None
    feature_vector: Optional[BehaviorFeatureVectorSchema] = None


class Module6SummarySchema(BaseModel):
    """Aggregate summary for Module 6 analysis."""
    total_sessions: int = 0
    segment_counts: Dict[str, int] = Field(default_factory=dict)
    segment_percentages: Dict[str, float] = Field(default_factory=dict)
    avg_confidence_per_segment: Dict[str, float] = Field(default_factory=dict)
    average_journey_duration_sec: float = 0.0
    average_path_efficiency: float = 0.0
    average_zones_per_shopper: float = 0.0


class JourneyStageEvent(BaseModel):
    """A single event in a shopper journey timeline."""
    timestamp: float = 0.0
    stage: str
    zone: Optional[str] = None
    shelf: Optional[str] = None
    product: Optional[str] = None
    event_type: Optional[str] = None
    duration: float = 0.0


class JourneyTimelineSchema(BaseModel):
    """Journey timeline for a shopper session."""
    session_id: Optional[str] = None
    track_id: Optional[int] = None
    status: str = "incomplete"
    timeline: List[JourneyStageEvent] = Field(default_factory=list)
    total_duration_sec: float = 0.0


class ZoneTransitionSchema(BaseModel):
    """Zone-to-zone transition record."""
    from_zone: str
    to_zone: str
    count: int = 0
    probability: float = 0.0


class FunnelStageSchema(BaseModel):
    """Funnel stage metrics."""
    stage: str
    shoppers: int = 0
    conversion_rate_pct: float = 0.0
    dropoff: int = 0
    dropoff_pct: float = 0.0


class FrictionPointSchema(BaseModel):
    """Friction point detection result."""
    shelf_id: str
    gaze_shoppers: int = 0
    interaction_shoppers: int = 0
    interaction_rate: float = 0.0
    is_friction_point: bool = True


class ProductPreferenceSchema(BaseModel):
    """Product preference score."""
    product_name: str
    product_id: str
    preference_score: float = 0.0
    views: int = 0
    pickups: int = 0
    returns: int = 0
    unique_interactors: int = 0
    dominant_shopper_segment: str = "EXPLORER"


class Module6AnalysisResponse(BaseModel):
    """Full Module 6 analysis response."""
    job_id: Optional[str] = None
    store_id: Optional[str] = None
    camera_id: Optional[str] = None
    summary: Module6SummarySchema = Field(default_factory=Module6SummarySchema)
    shopper_segments: List[ShopperClassificationSchema] = Field(default_factory=list)
    journeys: List[JourneyTimelineSchema] = Field(default_factory=list)
    zone_transitions: Dict[str, Any] = Field(default_factory=dict)
    funnel: Dict[str, Any] = Field(default_factory=dict)
    friction_points: List[FrictionPointSchema] = Field(default_factory=list)
    product_preferences: List[ProductPreferenceSchema] = Field(default_factory=list)


class Module6TriggerResponse(BaseModel):
    """Response after triggering Module 6 analysis."""
    job_id: str
    status: str = "completed"
    message: str = "Module 6 behavior analysis completed successfully"
    summary: Optional[Module6SummarySchema] = None
