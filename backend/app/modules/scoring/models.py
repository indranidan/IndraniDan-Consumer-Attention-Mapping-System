"""
Module 8 — Product Attractiveness Scoring Data Models
=======================================================
Domain data structures for the Module 8 scoring engine:
- PillarScores: five normalized sub-score vector
- ProductScoreProfile: per-SKU complete score card
- ShelfVisibilityProfile: shelf tier visibility & ergonomic bias
- ScoringConfidence: sample size and confidence rating
- Module8Summary: overall scoring job summary
- QualitativeRating: letter-grade enum (A+ through D)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QualitativeRating(str, Enum):
    """Letter-grade qualitative rating bands for attractiveness scores."""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"

    @classmethod
    def from_score(cls, score: float) -> "QualitativeRating":
        """Derive letter grade from a 0-100 score."""
        if score >= 90.0:
            return cls.A_PLUS
        elif score >= 75.0:
            return cls.A
        elif score >= 55.0:
            return cls.B
        elif score >= 35.0:
            return cls.C
        else:
            return cls.D


class ShelfTier(str, Enum):
    """Vertical shelf tier classifications with ergonomic visibility factors."""
    TOP = "TOP"
    EYE_LEVEL = "EYE_LEVEL"
    TOUCH = "TOUCH"
    BOTTOM = "BOTTOM"
    UNKNOWN = "UNKNOWN"


# Ergonomic visibility coefficients per tier
SHELF_TIER_GAMMA: Dict[ShelfTier, float] = {
    ShelfTier.TOP: 0.70,
    ShelfTier.EYE_LEVEL: 1.00,
    ShelfTier.TOUCH: 0.85,
    ShelfTier.BOTTOM: 0.40,
    ShelfTier.UNKNOWN: 0.75,
}


class ConfidenceLevel(str, Enum):
    """Confidence level labels for sample size adequacy."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class ScoringConfidence:
    """Sample size awareness and confidence rating for a scored product."""
    sample_size: int = 0
    confidence_score: float = 0.0  # 0.0 to 1.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    threshold_used: int = 10

    @classmethod
    def compute(cls, sample_size: int, threshold: int = 10) -> "ScoringConfidence":
        """Compute confidence from observation count using asymptotic curve."""
        raw = 1.0 - (1.0 / (1.0 + (sample_size / max(1, threshold)) ** 0.5))
        score = round(min(1.0, max(0.0, raw)), 4)
        if score >= 0.75:
            level = ConfidenceLevel.HIGH
        elif score >= 0.45:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        return cls(
            sample_size=sample_size,
            confidence_score=score,
            confidence_level=level,
            threshold_used=threshold,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "threshold_used": self.threshold_used,
        }


@dataclass
class PillarScores:
    """Five-pillar normalized sub-score vector (each 0.0 to 1.0)."""
    attention_score: float = 0.0
    interaction_score: float = 0.0
    pickup_score: float = 0.0
    conversion_score: float = 0.0
    repeat_score: float = 0.0

    # Weights
    W_ATTENTION: float = 0.35
    W_INTERACTION: float = 0.25
    W_PICKUP: float = 0.20
    W_CONVERSION: float = 0.15
    W_REPEAT: float = 0.05

    @property
    def composite_score(self) -> float:
        """Weighted composite attractiveness score (0-100)."""
        raw = (
            self.W_ATTENTION * self.attention_score
            + self.W_INTERACTION * self.interaction_score
            + self.W_PICKUP * self.pickup_score
            + self.W_CONVERSION * self.conversion_score
            + self.W_REPEAT * self.repeat_score
        )
        return round(min(100.0, max(0.0, raw * 100.0)), 2)

    @property
    def rating(self) -> QualitativeRating:
        return QualitativeRating.from_score(self.composite_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attention_score": round(self.attention_score, 4),
            "interaction_score": round(self.interaction_score, 4),
            "pickup_score": round(self.pickup_score, 4),
            "conversion_score": round(self.conversion_score, 4),
            "repeat_score": round(self.repeat_score, 4),
            "composite_score": self.composite_score,
            "rating": self.rating.value,
        }


@dataclass
class ShelfVisibilityProfile:
    """Shelf tier visibility score and ergonomic bias data for a product."""
    shelf_id: str = ""
    shelf_name: str = ""
    shelf_tier: ShelfTier = ShelfTier.UNKNOWN
    gamma_coefficient: float = 0.75
    visibility_score: float = 0.0  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name,
            "shelf_tier": self.shelf_tier.value,
            "gamma_coefficient": self.gamma_coefficient,
            "visibility_score": round(self.visibility_score, 2),
        }


@dataclass
class ProductScoreProfile:
    """Complete Module 8 score card for a single product / SKU."""
    product_id: str
    product_name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    shelf_id: Optional[str] = None
    shelf_name: Optional[str] = None

    # Raw telemetry inputs
    total_viewers: int = 0
    total_passersby: int = 0
    total_attention_duration_sec: float = 0.0
    average_attention_duration_sec: float = 0.0
    total_interactions: int = 0
    total_pickups: int = 0
    total_returns: int = 0
    total_purchases: int = 0
    repeat_interactions: int = 0
    unique_shoppers: int = 0

    # Computed scores
    pillar_scores: PillarScores = field(default_factory=PillarScores)
    shelf_visibility: ShelfVisibilityProfile = field(default_factory=ShelfVisibilityProfile)
    confidence: ScoringConfidence = field(default_factory=ScoringConfidence)

    # Derived composite metrics
    attractiveness_score: float = 0.0  # 0-100 composite
    intrinsic_attractiveness_score: float = 0.0  # Tier-adjusted
    engagement_score: float = 0.0  # 0-100
    conversion_potential_score: float = 0.0  # 0-100
    marketing_effectiveness_score: float = 0.0  # 0-100

    rating: QualitativeRating = QualitativeRating.D

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "sku": self.sku,
            "category": self.category,
            "shelf_id": self.shelf_id,
            "shelf_name": self.shelf_name,
            "total_viewers": self.total_viewers,
            "total_passersby": self.total_passersby,
            "total_attention_duration_sec": round(self.total_attention_duration_sec, 3),
            "average_attention_duration_sec": round(self.average_attention_duration_sec, 3),
            "total_interactions": self.total_interactions,
            "total_pickups": self.total_pickups,
            "total_returns": self.total_returns,
            "total_purchases": self.total_purchases,
            "repeat_interactions": self.repeat_interactions,
            "unique_shoppers": self.unique_shoppers,
            "pillar_scores": self.pillar_scores.to_dict(),
            "shelf_visibility": self.shelf_visibility.to_dict(),
            "confidence": self.confidence.to_dict(),
            "attractiveness_score": round(self.attractiveness_score, 2),
            "intrinsic_attractiveness_score": round(self.intrinsic_attractiveness_score, 2),
            "engagement_score": round(self.engagement_score, 2),
            "conversion_potential_score": round(self.conversion_potential_score, 2),
            "marketing_effectiveness_score": round(self.marketing_effectiveness_score, 2),
            "rating": self.rating.value,
        }


@dataclass
class Module8Summary:
    """Overall summary of Module 8 scoring for a job."""
    total_products_scored: int = 0
    average_attractiveness_score: float = 0.0
    top_performer_id: Optional[str] = None
    top_performer_name: Optional[str] = None
    top_performer_score: float = 0.0
    bottom_performer_id: Optional[str] = None
    bottom_performer_name: Optional[str] = None
    bottom_performer_score: float = 0.0
    average_confidence: float = 0.0
    insufficient_data: bool = False
    config_hash: Optional[str] = None
    analyzed_at: Optional[str] = None
    version: str = "1.0"
    disclaimer: str = (
        "Module 8 computes product attractiveness scores from Module 3/4/5 telemetry. "
        "Scores are normalized against traffic opportunities and smoothed with Bayesian "
        "priors for low-sample SKUs. Shelf visibility adjustments use standard ergonomic "
        "tier coefficients."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_products_scored": self.total_products_scored,
            "average_attractiveness_score": round(self.average_attractiveness_score, 2),
            "top_performer_id": self.top_performer_id,
            "top_performer_name": self.top_performer_name,
            "top_performer_score": round(self.top_performer_score, 2),
            "bottom_performer_id": self.bottom_performer_id,
            "bottom_performer_name": self.bottom_performer_name,
            "bottom_performer_score": round(self.bottom_performer_score, 2),
            "average_confidence": round(self.average_confidence, 4),
            "insufficient_data": self.insufficient_data,
            "config_hash": self.config_hash,
            "analyzed_at": self.analyzed_at,
            "version": self.version,
            "disclaimer": self.disclaimer,
        }
