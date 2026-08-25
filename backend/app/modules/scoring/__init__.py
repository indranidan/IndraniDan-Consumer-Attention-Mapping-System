"""
Module 8 — Product Attractiveness Scoring Engine
==================================================
Master package for Module 8:
- Multi-Factor Weighted Attractiveness Scoring (5-pillar suite)
- Foot-Traffic Exposure & Impression Normalization
- Empirical Bayes Smoothing for Cold-Start SKUs
- Shelf Visibility & Planogram Bias Correction
- Structured JSON & Markdown Intelligence Reports
"""

from app.modules.scoring.models import (
    PillarScores,
    ProductScoreProfile,
    ShelfVisibilityProfile,
    ScoringConfidence,
    Module8Summary,
    QualitativeRating,
)

__all__ = [
    "PillarScores",
    "ProductScoreProfile",
    "ShelfVisibilityProfile",
    "ScoringConfidence",
    "Module8Summary",
    "QualitativeRating",
]


def __getattr__(name: str):
    """Lazy imports for engine and report generator to avoid circular import errors."""
    if name == "Module8ScoringEngine":
        from app.modules.scoring.engine import Module8ScoringEngine
        return Module8ScoringEngine
    if name == "Module8ReportGenerator":
        from app.modules.scoring.report_generator import Module8ReportGenerator
        return Module8ReportGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
