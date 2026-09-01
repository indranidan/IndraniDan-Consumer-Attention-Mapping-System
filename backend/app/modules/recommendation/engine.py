"""
Module 9 — Recommendation & Optimization Engine
==================================================
Core orchestrator that:
1. Accepts Module 8 product score profiles and telemetry data
2. Dispatches evaluation to modular rule subsystems
3. Collects, deduplicates, and ROI-ranks all generated recommendations
4. Produces a Module9Summary with categorized priority breakdowns

Reuses existing Module 8 scoring outputs without re-running the scoring pipeline.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.recommendation.models import (
    ActionableRecommendation,
    ExpectedImpact,
    Module9Summary,
    RecommendationCategory,
    RecommendationPriority,
)


class Module9RecommendationEngine:
    """
    Master Recommendation Engine for Module 9.

    Coordinates five rule evaluator subsystems:
    - shelf_rules: Tier optimization and facing rebalancing
    - placement_rules: Pairwise swaps and co-merchandising affinity
    - promo_rules: Promotional endcap and signage nominations
    - friction_rules: Shopper funnel friction interventions
    - layout_rules: Dead zone activation and congestion mitigation
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("module9_engine")

    def generate_recommendations(
        self,
        product_profiles: List[Dict[str, Any]],
        heatmap_data: Optional[Dict[str, Any]] = None,
        behavior_data: Optional[Dict[str, Any]] = None,
        store_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run all rule evaluators and produce a ranked set of recommendations.

        Parameters
        ----------
        product_profiles : list
            List of Module 8 ProductScoreProfile dicts (from scoring engine).
        heatmap_data : dict, optional
            Module 7 heatmap/hotspot data for layout rules.
        behavior_data : dict, optional
            Module 6 behavior segmentation data for layout rules.
        store_id : str, optional
            Store identifier for contextual recommendations.

        Returns
        -------
        dict with keys: "recommendations", "summary"
        """
        all_recommendations: List[ActionableRecommendation] = []

        # Import rule evaluators lazily to avoid circular imports
        from app.modules.recommendation.shelf_rules import evaluate_shelf_rules
        from app.modules.recommendation.placement_rules import evaluate_placement_rules
        from app.modules.recommendation.promo_rules import evaluate_promo_rules
        from app.modules.recommendation.friction_rules import evaluate_friction_rules
        from app.modules.recommendation.layout_rules import evaluate_layout_rules

        # 1. Shelf Optimization Rules
        try:
            shelf_recs = evaluate_shelf_rules(product_profiles)
            all_recommendations.extend(shelf_recs)
            self.logger.info(f"Shelf rules generated {len(shelf_recs)} recommendations")
        except Exception as exc:
            self.logger.warning(f"Shelf rules evaluation failed: {exc}")

        # 2. Product Placement Rules
        try:
            placement_recs = evaluate_placement_rules(product_profiles)
            all_recommendations.extend(placement_recs)
            self.logger.info(f"Placement rules generated {len(placement_recs)} recommendations")
        except Exception as exc:
            self.logger.warning(f"Placement rules evaluation failed: {exc}")

        # 3. Promotional Placement Rules
        try:
            promo_recs = evaluate_promo_rules(product_profiles)
            all_recommendations.extend(promo_recs)
            self.logger.info(f"Promo rules generated {len(promo_recs)} recommendations")
        except Exception as exc:
            self.logger.warning(f"Promo rules evaluation failed: {exc}")

        # 4. Consumer Engagement & Friction Rules
        try:
            friction_recs = evaluate_friction_rules(product_profiles)
            all_recommendations.extend(friction_recs)
            self.logger.info(f"Friction rules generated {len(friction_recs)} recommendations")
        except Exception as exc:
            self.logger.warning(f"Friction rules evaluation failed: {exc}")

        # 5. Layout & Traffic Flow Rules
        try:
            layout_recs = evaluate_layout_rules(
                product_profiles,
                heatmap_data=heatmap_data,
                behavior_data=behavior_data,
            )
            all_recommendations.extend(layout_recs)
            self.logger.info(f"Layout rules generated {len(layout_recs)} recommendations")
        except Exception as exc:
            self.logger.warning(f"Layout rules evaluation failed: {exc}")

        # Sort by composite impact score descending, then by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
        }
        all_recommendations.sort(
            key=lambda r: (
                priority_order.get(r.priority, 4),
                -r.expected_impact.composite_impact_score,
            )
        )

        # Build summary
        summary = self._build_summary(all_recommendations)

        return {
            "recommendations": [r.to_dict() for r in all_recommendations],
            "summary": summary.to_dict(),
        }

    def _build_summary(
        self, recommendations: List[ActionableRecommendation]
    ) -> Module9Summary:
        """Compile overall Module 9 summary statistics."""
        total = len(recommendations)
        critical = sum(1 for r in recommendations if r.priority == RecommendationPriority.CRITICAL)
        high = sum(1 for r in recommendations if r.priority == RecommendationPriority.HIGH)
        medium = sum(1 for r in recommendations if r.priority == RecommendationPriority.MEDIUM)
        low = sum(1 for r in recommendations if r.priority == RecommendationPriority.LOW)

        categories_breakdown: Dict[str, int] = {}
        for r in recommendations:
            cat = r.category.value
            categories_breakdown[cat] = categories_breakdown.get(cat, 0) + 1

        avg_impact = 0.0
        if total > 0:
            avg_impact = sum(
                r.expected_impact.composite_impact_score for r in recommendations
            ) / total

        top_title = recommendations[0].title if recommendations else None

        return Module9Summary(
            total_recommendations=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            categories_breakdown=categories_breakdown,
            top_recommendation_title=top_title,
            average_impact_score=avg_impact,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )
