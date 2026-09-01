"""
Module 9 — What-If Planogram Simulator
=========================================
Stateless simulation engine that computes projected score lifts
for hypothetical shelf tier swaps and facing count adjustments.

All calculations are in-memory with no database mutations.
"""

import logging
import math
from typing import Optional

from app.modules.recommendation.models import (
    PlanogramSimulationRequest,
    PlanogramSimulationResult,
)
from app.modules.scoring.models import SHELF_TIER_GAMMA, ShelfTier


logger = logging.getLogger("module9_simulator")


# ── Tier resolution ───────────────────────────────────────────

_TIER_MAP = {
    "EYE_LEVEL": ShelfTier.EYE_LEVEL,
    "TOP": ShelfTier.TOP,
    "TOUCH": ShelfTier.TOUCH,
    "BOTTOM": ShelfTier.BOTTOM,
    "UNKNOWN": ShelfTier.UNKNOWN,
}


def _resolve_gamma(tier_str: str) -> float:
    """Resolve gamma coefficient from tier string."""
    tier = _TIER_MAP.get(tier_str.upper(), ShelfTier.UNKNOWN)
    return SHELF_TIER_GAMMA.get(tier, 0.75)


class PlanogramSimulator:
    """
    Stateless What-If simulation engine for planogram alterations.

    Computes projected visibility scores, attractiveness adjustments,
    and percentage lift estimates without any database side effects.
    """

    @staticmethod
    def simulate(request: PlanogramSimulationRequest) -> PlanogramSimulationResult:
        """
        Simulate a hypothetical shelf tier move or facing count adjustment.

        Parameters
        ----------
        request : PlanogramSimulationRequest
            Contains current and target tier, facing counts, and baseline scores.

        Returns
        -------
        PlanogramSimulationResult
            Projected scores and percentage lifts.
        """
        original_gamma = _resolve_gamma(request.current_shelf_tier)
        simulated_gamma = _resolve_gamma(request.target_shelf_tier)

        # Compute visibility scores
        original_visibility = min(100.0, original_gamma * 100.0)
        simulated_visibility = min(100.0, simulated_gamma * 100.0)

        # Facing count multiplier (logarithmic diminishing returns)
        facing_multiplier = 1.0
        if request.target_facing_count != request.current_facing_count and request.current_facing_count > 0:
            facing_ratio = request.target_facing_count / request.current_facing_count
            facing_multiplier = 1.0 + 0.15 * math.log(max(0.1, facing_ratio))

        # Simulated attractiveness: rescale observed score by gamma ratio
        gamma_ratio = simulated_gamma / max(0.2, original_gamma)
        simulated_attractiveness = min(
            100.0,
            request.current_attractiveness_score * gamma_ratio * facing_multiplier,
        )

        # Attention lift: percentage change in visibility-adjusted score
        if request.current_attractiveness_score > 0:
            attention_lift = (
                (simulated_attractiveness - request.current_attractiveness_score)
                / request.current_attractiveness_score
                * 100.0
            )
        else:
            attention_lift = 0.0

        # Conversion lift: empirically ~35% of attention lift
        conversion_lift = attention_lift * 0.35

        # Determine if this is an improvement
        is_improvement = simulated_attractiveness > request.current_attractiveness_score

        return PlanogramSimulationResult(
            product_id=request.product_id,
            original_tier=request.current_shelf_tier,
            simulated_tier=request.target_shelf_tier,
            original_gamma=original_gamma,
            simulated_gamma=simulated_gamma,
            original_visibility_score=round(original_visibility, 2),
            simulated_visibility_score=round(simulated_visibility, 2),
            original_attractiveness_score=round(request.current_attractiveness_score, 2),
            simulated_attractiveness_score=round(simulated_attractiveness, 2),
            attention_lift_pct=round(attention_lift, 2),
            conversion_lift_pct=round(conversion_lift, 2),
            facing_change=request.target_facing_count - request.current_facing_count,
            is_improvement=is_improvement,
        )
