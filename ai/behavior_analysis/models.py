"""
Module 6 — Consumer Behavior Data Models
==========================================
Domain data structures for behavioral feature vectors, shopper archetypes,
classification results, and summary aggregations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ShopperArchetype(str, Enum):
    """Five behavioral shopper archetypes."""
    EXPLORER = "EXPLORER"
    QUICK_BUYER = "QUICK_BUYER"
    COMPARISON_SHOPPER = "COMPARISON_SHOPPER"
    IMPULSE_BUYER = "IMPULSE_BUYER"
    BRAND_LOYAL = "BRAND_LOYAL"


@dataclass
class BehaviorFeatureVector:
    """Computed behavioral features for a single shopper session."""
    path_efficiency: float = 0.0
    dwell_to_transit_ratio: float = 0.0
    zone_breadth: int = 0
    gaze_alternation_rate: float = 0.0
    pickup_to_return_ratio: float = 0.0
    brand_concentration: float = 0.0
    promo_deviation_count: int = 0
    has_reduced_confidence: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_efficiency": round(self.path_efficiency, 4),
            "dwell_to_transit_ratio": round(self.dwell_to_transit_ratio, 4),
            "zone_breadth": self.zone_breadth,
            "gaze_alternation_rate": round(self.gaze_alternation_rate, 4),
            "pickup_to_return_ratio": round(self.pickup_to_return_ratio, 4),
            "brand_concentration": round(self.brand_concentration, 4),
            "promo_deviation_count": self.promo_deviation_count,
            "has_reduced_confidence": self.has_reduced_confidence,
        }


@dataclass
class ShopperClassification:
    """Classification result for a single shopper session."""
    track_id: int
    session_id: Optional[str] = None
    primary_segment: ShopperArchetype = ShopperArchetype.EXPLORER
    confidence: float = 0.0
    secondary_segment: Optional[ShopperArchetype] = None
    feature_vector: Optional[BehaviorFeatureVector] = None
    probabilities: Optional[Dict[str, float]] = None
    conversion_probability: float = 0.0
    model_type: str = "heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "session_id": self.session_id,
            "primary_segment": self.primary_segment.value if isinstance(self.primary_segment, ShopperArchetype) else str(self.primary_segment),
            "confidence": round(self.confidence, 4),
            "secondary_segment": self.secondary_segment.value if isinstance(self.secondary_segment, ShopperArchetype) else None,
            "feature_vector": self.feature_vector.to_dict() if self.feature_vector else None,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()} if self.probabilities else None,
            "conversion_probability": round(self.conversion_probability, 4),
            "model_type": self.model_type,
        }


@dataclass
class Module6Summary:
    """Aggregate summary statistics for Module 6 analysis."""
    total_sessions: int = 0
    segment_counts: Dict[str, int] = field(default_factory=dict)
    segment_percentages: Dict[str, float] = field(default_factory=dict)
    avg_confidence_per_segment: Dict[str, float] = field(default_factory=dict)
    average_journey_duration_sec: float = 0.0
    average_path_efficiency: float = 0.0
    average_zones_per_shopper: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "segment_counts": self.segment_counts,
            "segment_percentages": {k: round(v, 2) for k, v in self.segment_percentages.items()},
            "avg_confidence_per_segment": {k: round(v, 4) for k, v in self.avg_confidence_per_segment.items()},
            "average_journey_duration_sec": round(self.average_journey_duration_sec, 2),
            "average_path_efficiency": round(self.average_path_efficiency, 4),
            "average_zones_per_shopper": round(self.average_zones_per_shopper, 2),
        }
