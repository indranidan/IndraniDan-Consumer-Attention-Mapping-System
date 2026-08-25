"""
Module 8 — Product Attractiveness Scoring Schemas
===================================================
Pydantic response models for Module 8 endpoints:
- Five-pillar score vectors
- Product score cards and leaderboards
- Shelf visibility profiles
- Confidence metrics
- Overall scoring summary and analysis response
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class PillarScoresSchema(BaseModel):
    """Five-pillar normalized sub-score vector."""
    attention_score: float = 0.0
    interaction_score: float = 0.0
    pickup_score: float = 0.0
    conversion_score: float = 0.0
    repeat_score: float = 0.0
    composite_score: float = 0.0
    rating: str = "D"


class ScoringConfidenceSchema(BaseModel):
    """Sample size confidence rating."""
    sample_size: int = 0
    confidence_score: float = 0.0
    confidence_level: str = "Low"
    threshold_used: int = 10


class ShelfVisibilitySchema(BaseModel):
    """Shelf tier visibility profile."""
    shelf_id: str = ""
    shelf_name: str = ""
    shelf_tier: str = "UNKNOWN"
    gamma_coefficient: float = 0.75
    visibility_score: float = 0.0


class ProductScoreCardItem(BaseModel):
    """Complete Module 8 score card for a single product / SKU."""
    product_id: str
    product_name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    shelf_id: Optional[str] = None
    shelf_name: Optional[str] = None

    # Raw telemetry
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
    pillar_scores: PillarScoresSchema = Field(default_factory=PillarScoresSchema)
    shelf_visibility: ShelfVisibilitySchema = Field(default_factory=ShelfVisibilitySchema)
    confidence: ScoringConfidenceSchema = Field(default_factory=ScoringConfidenceSchema)

    # Derived composite metrics
    attractiveness_score: float = 0.0
    intrinsic_attractiveness_score: float = 0.0
    engagement_score: float = 0.0
    conversion_potential_score: float = 0.0
    marketing_effectiveness_score: float = 0.0
    rating: str = "D"


class LeaderboardItem(BaseModel):
    """Compact leaderboard entry for ranking display."""
    rank: int
    product_id: str
    product_name: str
    sku: Optional[str] = None
    attractiveness_score: float = 0.0
    rating: str = "D"
    confidence_level: str = "Low"
    intrinsic_attractiveness_score: float = 0.0


class Module8SummarySchema(BaseModel):
    """Overall summary for Module 8 scoring."""
    total_products_scored: int = 0
    average_attractiveness_score: float = 0.0
    top_performer_id: Optional[str] = None
    top_performer_name: Optional[str] = None
    top_performer_score: float = 0.0
    bottom_performer_id: Optional[str] = None
    bottom_performer_name: Optional[str] = None
    bottom_performer_score: float = 0.0
    average_confidence: float = 0.0
    config_hash: Optional[str] = None
    analyzed_at: Optional[str] = None
    version: str = "1.0"
    disclaimer: str = (
        "Module 8 computes product attractiveness scores from Module 3/4/5 telemetry. "
        "Scores are normalized against traffic opportunities and smoothed with Bayesian "
        "priors for low-sample SKUs."
    )


class Module8AnalysisResponse(BaseModel):
    """Full Module 8 scoring analysis response."""
    job_id: uuid.UUID
    camera_id: uuid.UUID
    store_id: uuid.UUID
    status: str = "COMPLETED"
    summary: Module8SummarySchema
    products: List[ProductScoreCardItem] = []
    total_products_scored: int = 0
    disclaimer: str = (
        "Module 8 computes product attractiveness scores from Module 3/4/5 telemetry. "
        "No fabricated scores are generated."
    )


class Module8LeaderboardResponse(BaseModel):
    """Leaderboard response for ranking display."""
    job_id: uuid.UUID
    top_performers: List[LeaderboardItem] = []
    bottom_performers: List[LeaderboardItem] = []
    total_products_scored: int = 0


class Module8ReportResponse(BaseModel):
    """Structured report data response."""
    job_id: uuid.UUID
    json_report: Dict[str, Any]
    markdown_report: str
