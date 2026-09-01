"""
Module 9 — Recommendation & Optimization Schemas
===================================================
Pydantic schemas for Module 9 endpoints:
- ActionableRecommendationSchema
- ExpectedImpactSchema
- Module9SummarySchema
- RecommendationResponse
- StoreRecommendationResponse
- PlanogramSimulationRequestSchema
- PlanogramSimulationResponse
"""

from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ExpectedImpactSchema(BaseModel):
    """Projected impact metrics for a recommendation."""
    attention_lift_pct: float = 0.0
    conversion_lift_pct: float = 0.0
    revenue_impact_estimate: Optional[float] = None
    confidence: float = 0.0


class ActionableRecommendationSchema(BaseModel):
    """Full actionable recommendation model."""
    id: str
    category: str
    priority: str
    title: str
    description: str
    target_type: str
    target_id: str
    target_name: str
    current_metrics: Dict[str, Any] = Field(default_factory=dict)
    proposed_action: str = ""
    expected_impact: ExpectedImpactSchema = Field(default_factory=ExpectedImpactSchema)
    rationale: str = ""
    shelf_swap_details: Optional[Dict[str, Any]] = None


class Module9SummarySchema(BaseModel):
    """Overall summary for Module 9 recommendations."""
    total_recommendations: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    categories_breakdown: Dict[str, int] = Field(default_factory=dict)
    top_recommendation_title: Optional[str] = None
    average_impact_score: float = 0.0
    analyzed_at: Optional[str] = None
    version: str = "1.0"
    disclaimer: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response payload for job-level recommendations."""
    job_id: str
    store_id: Optional[str] = None
    recommendations: List[ActionableRecommendationSchema]
    summary: Module9SummarySchema
    total: int


class StoreRecommendationResponse(BaseModel):
    """Response payload for store-level recommendations."""
    store_id: str
    recommendations: List[ActionableRecommendationSchema]
    total: int
    jobs_analyzed: int


class PlanogramSimulationRequestSchema(BaseModel):
    """Request payload for What-If planogram simulation."""
    product_id: str
    current_shelf_tier: str
    target_shelf_tier: str
    current_facing_count: int = 1
    target_facing_count: int = 1
    current_attractiveness_score: float = 0.0
    current_intrinsic_score: float = 0.0


class PlanogramSimulationResponse(BaseModel):
    """Response payload from What-If planogram simulation."""
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
