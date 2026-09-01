"""
Module 9 — Recommendation & Optimization Data Models
=======================================================
Domain data structures for the Module 9 recommendation engine:
- RecommendationCategory: 5 core optimization disciplines
- RecommendationPriority: urgency and ROI ranking levels
- ExpectedImpact: projected attention, conversion, and revenue lifts
- ActionableRecommendation: full recommendation payload
- PlanogramSimulationRequest/Result: What-If simulation contracts
- Module9Summary: overall recommendation generation summary
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RecommendationCategory(str, Enum):
    """Core optimization disciplines for retail merchandising."""
    SHELF_OPTIMIZATION = "SHELF_OPTIMIZATION"
    PRODUCT_PLACEMENT = "PRODUCT_PLACEMENT"
    PROMOTIONAL_PLACEMENT = "PROMOTIONAL_PLACEMENT"
    CONSUMER_ENGAGEMENT = "CONSUMER_ENGAGEMENT"
    LAYOUT_IMPROVEMENT = "LAYOUT_IMPROVEMENT"


class RecommendationPriority(str, Enum):
    """Priority / urgency levels ranked by estimated ROI impact."""
    CRITICAL = "CRITICAL"   # Immediate ROI / severe bottleneck
    HIGH = "HIGH"           # Significant revenue or attention lift
    MEDIUM = "MEDIUM"       # Moderate optimization
    LOW = "LOW"             # Incremental refinement

    @classmethod
    def from_impact_score(cls, score: float) -> "RecommendationPriority":
        """Derive priority from a composite impact score (0-100)."""
        if score >= 80.0:
            return cls.CRITICAL
        elif score >= 55.0:
            return cls.HIGH
        elif score >= 30.0:
            return cls.MEDIUM
        else:
            return cls.LOW


@dataclass
class ExpectedImpact:
    """Projected impact metrics for a recommendation."""
    attention_lift_pct: float = 0.0
    conversion_lift_pct: float = 0.0
    revenue_impact_estimate: Optional[float] = None
    confidence: float = 0.0  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attention_lift_pct": round(self.attention_lift_pct, 2),
            "conversion_lift_pct": round(self.conversion_lift_pct, 2),
            "revenue_impact_estimate": self.revenue_impact_estimate,
            "confidence": round(self.confidence, 4),
        }

    @property
    def composite_impact_score(self) -> float:
        """Weighted composite impact for sorting: 60% attention + 40% conversion."""
        return round(
            0.6 * min(100.0, self.attention_lift_pct)
            + 0.4 * min(100.0, self.conversion_lift_pct),
            2,
        )


@dataclass
class ActionableRecommendation:
    """Full recommendation payload for a single merchandising action."""
    id: str
    category: RecommendationCategory
    priority: RecommendationPriority
    title: str
    description: str
    target_type: str        # "PRODUCT" | "SHELF" | "ZONE" | "STORE"
    target_id: str          # e.g., SKU id or shelf id
    target_name: str
    current_metrics: Dict[str, Any] = field(default_factory=dict)
    proposed_action: str = ""
    expected_impact: ExpectedImpact = field(default_factory=ExpectedImpact)
    rationale: str = ""
    shelf_swap_details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "category": self.category.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "current_metrics": self.current_metrics,
            "proposed_action": self.proposed_action,
            "expected_impact": self.expected_impact.to_dict(),
            "rationale": self.rationale,
        }
        if self.shelf_swap_details:
            result["shelf_swap_details"] = self.shelf_swap_details
        return result


@dataclass
class PlanogramSimulationRequest:
    """Request payload for a What-If planogram simulation."""
    product_id: str
    current_shelf_tier: str      # e.g., "BOTTOM", "TOUCH", "EYE_LEVEL", "TOP"
    target_shelf_tier: str       # e.g., "EYE_LEVEL"
    current_facing_count: int = 1
    target_facing_count: int = 1
    current_attractiveness_score: float = 0.0
    current_intrinsic_score: float = 0.0


@dataclass
class PlanogramSimulationResult:
    """Result payload from a What-If planogram simulation."""
    product_id: str
    original_tier: str
    simulated_tier: str
    original_gamma: float
    simulated_gamma: float
    original_visibility_score: float
    simulated_visibility_score: float
    original_attractiveness_score: float
    simulated_attractiveness_score: float
    attention_lift_pct: float
    conversion_lift_pct: float
    facing_change: int = 0
    is_improvement: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "original_tier": self.original_tier,
            "simulated_tier": self.simulated_tier,
            "original_gamma": round(self.original_gamma, 4),
            "simulated_gamma": round(self.simulated_gamma, 4),
            "original_visibility_score": round(self.original_visibility_score, 2),
            "simulated_visibility_score": round(self.simulated_visibility_score, 2),
            "original_attractiveness_score": round(self.original_attractiveness_score, 2),
            "simulated_attractiveness_score": round(self.simulated_attractiveness_score, 2),
            "attention_lift_pct": round(self.attention_lift_pct, 2),
            "conversion_lift_pct": round(self.conversion_lift_pct, 2),
            "facing_change": self.facing_change,
            "is_improvement": self.is_improvement,
        }


@dataclass
class Module9Summary:
    """Overall summary of Module 9 recommendation generation for a job."""
    total_recommendations: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    categories_breakdown: Dict[str, int] = field(default_factory=dict)
    top_recommendation_title: Optional[str] = None
    average_impact_score: float = 0.0
    analyzed_at: Optional[str] = None
    version: str = "1.0"
    disclaimer: str = (
        "Module 9 generates prescriptive merchandising recommendations from "
        "Module 3-8 telemetry. Recommendations are rule-based heuristics with "
        "projected impact estimates. Verify recommendations against store-specific "
        "operational constraints before implementation."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_recommendations": self.total_recommendations,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "categories_breakdown": self.categories_breakdown,
            "top_recommendation_title": self.top_recommendation_title,
            "average_impact_score": round(self.average_impact_score, 2),
            "analyzed_at": self.analyzed_at,
            "version": self.version,
            "disclaimer": self.disclaimer,
        }
