"""
Module 6 — Behavioral Segmentation Classifier
================================================
Hybrid ML & Rule-based classification of shopper sessions into five archetypes:
1. Supervised XGBoost multi-class classifier with probability calibration.
2. Calibrated rule-based scoring engine for transparent fallback.
"""

import logging
from typing import Optional

from ai.behavior_analysis.config import BehaviorConfig
from ai.behavior_analysis.models import (
    BehaviorFeatureVector,
    ShopperArchetype,
    ShopperClassification,
)
from ai.behavior_analysis.xgb_classifier import XGBBehaviorClassifier


logger = logging.getLogger("behavior_classifier")


class BehaviorClassifier:
    """Classifies shopper sessions into behavioral archetypes using ML with heuristic fallback."""

    def __init__(self):
        self.xgb_classifier = XGBBehaviorClassifier()

    def classify(
        self,
        feature_vector: BehaviorFeatureVector,
        config: BehaviorConfig,
        track_id: int = 0,
        session_id: Optional[str] = None,
        prefer_ml: bool = True,
    ) -> ShopperClassification:
        """
        Classify a shopper session into a behavioral archetype.
        Uses XGBoost when available, otherwise falls back to rule-based scoring.
        """
        # ── 1. Try Supervised XGBoost Classifier ───────────────────────────
        if prefer_ml and self.xgb_classifier.is_available and not feature_vector.has_reduced_confidence:
            ml_result = self.xgb_classifier.classify(
                feature_vector=feature_vector,
                track_id=track_id,
                session_id=session_id,
            )
            if ml_result is not None:
                return ml_result

        # ── 2. Fallback: Calibrated Rule-Based Scoring ──────────────────────
        return self._classify_heuristic(
            feature_vector=feature_vector,
            config=config,
            track_id=track_id,
            session_id=session_id,
        )

    def _classify_heuristic(
        self,
        feature_vector: BehaviorFeatureVector,
        config: BehaviorConfig,
        track_id: int = 0,
        session_id: Optional[str] = None,
    ) -> ShopperClassification:
        """
        Apply archetype classification rules in priority order:
        1. Brand Loyal (strongest specific signal)
        2. Comparison Shopper (high gaze alternation + returns)
        3. Impulse Buyer (promo deviation)
        4. Quick Buyer (direct path, low zone breadth)
        5. Explorer (default / wandering pattern)
        """
        scores = self._compute_archetype_scores(feature_vector, config)

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = ranked[0][0]
        primary_score = ranked[0][1]
        secondary = ranked[1][0] if len(ranked) > 1 else None
        secondary_score = ranked[1][1] if len(ranked) > 1 else 0.0

        # Compute confidence: how much primary dominates over secondary
        total = sum(s for _, s in ranked) or 1.0
        confidence = primary_score / total

        # If top two are very close, mark secondary and lower confidence
        if secondary_score > 0 and (primary_score - secondary_score) / max(primary_score, 0.001) < 0.2:
            secondary_segment = secondary
        else:
            secondary_segment = None

        # Build normalized probability distribution
        prob_dict = {k.value if isinstance(k, ShopperArchetype) else str(k): round(v / total, 4) for k, v in scores.items()}

        # Estimate conversion intent
        conversion_prob = float(
            0.4 * prob_dict.get("BRAND_LOYAL", 0.0)
            + 0.35 * prob_dict.get("QUICK_BUYER", 0.0)
            + 0.25 * prob_dict.get("IMPULSE_BUYER", 0.0)
            + 0.15 * prob_dict.get("COMPARISON_SHOPPER", 0.0)
            + 0.05 * prob_dict.get("EXPLORER", 0.0)
        )

        return ShopperClassification(
            track_id=track_id,
            session_id=session_id,
            primary_segment=primary,
            confidence=min(confidence, 1.0),
            secondary_segment=secondary_segment,
            feature_vector=feature_vector,
            probabilities=prob_dict,
            conversion_probability=min(1.0, max(0.0, conversion_prob)),
            model_type="heuristic",
        )

    def _compute_archetype_scores(
        self, fv: BehaviorFeatureVector, cfg: BehaviorConfig
    ) -> dict:
        """Compute a raw score (0.0–1.0) for each archetype."""
        scores = {}

        # ── Brand Loyal ─────────────────────────────────────────
        brand_score = 0.0
        if fv.brand_concentration >= cfg.brand_loyalty_concentration_min:
            brand_score = 0.5 + 0.5 * min(fv.brand_concentration / 1.0, 1.0)
            if fv.gaze_alternation_rate <= cfg.brand_loyalty_max_gaze_alternation:
                brand_score += 0.2
        scores[ShopperArchetype.BRAND_LOYAL] = min(brand_score, 1.0)

        # ── Comparison Shopper ──────────────────────────────────
        comp_score = 0.0
        if fv.gaze_alternation_rate >= cfg.comparison_gaze_alternation_min:
            comp_score = 0.5 + 0.3 * min(fv.gaze_alternation_rate / 5.0, 1.0)
        if fv.pickup_to_return_ratio < 1.0 and fv.pickup_to_return_ratio > 0:
            comp_score += 0.2  # More returns than pure pickups
        scores[ShopperArchetype.COMPARISON_SHOPPER] = min(comp_score, 1.0)

        # ── Impulse Buyer ───────────────────────────────────────
        impulse_score = 0.0
        if fv.promo_deviation_count >= cfg.impulse_min_promo_deviations:
            impulse_score = 0.5 + 0.2 * min(fv.promo_deviation_count / 3.0, 1.0)
            if fv.gaze_alternation_rate < cfg.comparison_gaze_alternation_min:
                impulse_score += 0.2  # Quick grab without comparison
        scores[ShopperArchetype.IMPULSE_BUYER] = min(impulse_score, 1.0)

        # ── Quick Buyer ─────────────────────────────────────────
        quick_score = 0.0
        if (fv.path_efficiency >= cfg.quick_buyer_path_efficiency_min
                and fv.zone_breadth <= cfg.quick_buyer_max_zones):
            quick_score = 0.5 + 0.3 * min(fv.path_efficiency / 1.0, 1.0)
            if fv.dwell_to_transit_ratio < 0.3:
                quick_score += 0.2  # Low dwell = fast transit
        scores[ShopperArchetype.QUICK_BUYER] = min(quick_score, 1.0)

        # ── Explorer ────────────────────────────────────────────
        explorer_score = 0.0
        if (fv.path_efficiency <= cfg.explorer_path_efficiency_max
                and fv.zone_breadth >= cfg.explorer_min_zones):
            explorer_score = 0.5 + 0.3 * (1.0 - fv.path_efficiency)
            if fv.dwell_to_transit_ratio > 0.5:
                explorer_score += 0.2
        else:
            explorer_score = 0.2
        scores[ShopperArchetype.EXPLORER] = min(explorer_score, 1.0)

        return scores
