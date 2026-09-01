"""
Module 9 — Recommendation & Optimization Engine
==================================================
Master package for Module 9:
- Shelf Tier Optimization & Planogram Rebalancing
- Pairwise Opportunity Swaps & Co-Merchandising Affinity
- Promotional Endcap & Signage Nominations
- Shopper Funnel Friction Interventions
- Store Layout & Traffic Flow Improvements
- Interactive "What-If" Planogram Simulation
"""

from app.modules.recommendation.models import (
    ActionableRecommendation,
    RecommendationCategory,
    RecommendationPriority,
    ExpectedImpact,
    PlanogramSimulationRequest,
    PlanogramSimulationResult,
    Module9Summary,
)

__all__ = [
    "ActionableRecommendation",
    "RecommendationCategory",
    "RecommendationPriority",
    "ExpectedImpact",
    "PlanogramSimulationRequest",
    "PlanogramSimulationResult",
    "Module9Summary",
]


def __getattr__(name: str):
    """Lazy imports for engine and simulator to avoid circular import errors."""
    if name == "Module9RecommendationEngine":
        from app.modules.recommendation.engine import Module9RecommendationEngine
        return Module9RecommendationEngine
    if name == "PlanogramSimulator":
        from app.modules.recommendation.simulator import PlanogramSimulator
        return PlanogramSimulator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
