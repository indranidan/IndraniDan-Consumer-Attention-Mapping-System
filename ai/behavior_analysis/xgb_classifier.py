"""
Module 6 — Supervised XGBoost Behavioral Classifier
===================================================
Machine-learning-based classification of retail shopper sessions into behavioral
archetypes with multi-class probability scoring and purchase conversion estimation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ai.behavior_analysis.models import (
    BehaviorFeatureVector,
    ShopperArchetype,
    ShopperClassification,
)

logger = logging.getLogger("xgb_behavior_classifier")

ARCHETYPE_MAP: Dict[int, ShopperArchetype] = {
    0: ShopperArchetype.EXPLORER,
    1: ShopperArchetype.QUICK_BUYER,
    2: ShopperArchetype.COMPARISON_SHOPPER,
    3: ShopperArchetype.IMPULSE_BUYER,
    4: ShopperArchetype.BRAND_LOYAL,
}

REVERSE_ARCHETYPE_MAP: Dict[ShopperArchetype, int] = {
    v: k for k, v in ARCHETYPE_MAP.items()
}

FEATURE_NAMES: List[str] = [
    "path_efficiency",
    "dwell_to_transit_ratio",
    "zone_breadth",
    "gaze_alternation_rate",
    "pickup_to_return_ratio",
    "brand_concentration",
    "promo_deviation_count",
]


class XGBBehaviorClassifier:
    """Supervised XGBoost classifier for shopper behavior segmentation."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or Path(__file__).parent / "models" / "xgb_shopper_model.json"
        self.model = None
        self._is_loaded = False
        self._load_model()

    def _load_model(self) -> bool:
        """Attempt to load trained XGBoost model from disk."""
        if self.model_path and self.model_path.exists():
            try:
                import xgboost as xgb
                self.model = xgb.XGBClassifier()
                self.model.load_model(str(self.model_path))
                self._is_loaded = True
                logger.info(f"Loaded trained XGBoost behavioral model from {self.model_path}")
                return True
            except Exception as e:
                logger.warning(f"Could not load XGBoost model from {self.model_path}: {e}")
                self._is_loaded = False
                return False
        return False

    @property
    def is_available(self) -> bool:
        return self._is_loaded and self.model is not None

    def feature_vector_to_array(self, fv: BehaviorFeatureVector) -> np.ndarray:
        """Convert a BehaviorFeatureVector dataclass into a 1D numpy array."""
        return np.array([
            fv.path_efficiency,
            min(fv.dwell_to_transit_ratio, 10.0),
            float(fv.zone_breadth),
            min(fv.gaze_alternation_rate, 20.0),
            min(fv.pickup_to_return_ratio, 10.0),
            fv.brand_concentration,
            float(fv.promo_deviation_count),
        ], dtype=np.float32).reshape(1, -1)

    def classify(
        self,
        feature_vector: BehaviorFeatureVector,
        track_id: int = 0,
        session_id: Optional[str] = None,
    ) -> Optional[ShopperClassification]:
        """
        Classify a feature vector using the trained XGBoost model.
        Returns None if model is not available or classification fails.
        """
        if not self.is_available:
            return None

        try:
            x = self.feature_vector_to_array(feature_vector)
            probs = self.model.predict_proba(x)[0]

            # Map probabilities to archetypes
            prob_dict: Dict[str, float] = {}
            for idx, prob in enumerate(probs):
                archetype = ARCHETYPE_MAP.get(idx, ShopperArchetype.EXPLORER)
                prob_dict[archetype.value] = float(prob)

            # Sort by probability descending
            ranked_indices = np.argsort(probs)[::-1]
            primary_idx = int(ranked_indices[0])
            primary_segment = ARCHETYPE_MAP[primary_idx]
            primary_prob = float(probs[primary_idx])

            secondary_segment = None
            if len(ranked_indices) > 1 and probs[ranked_indices[1]] > 0.15:
                secondary_segment = ARCHETYPE_MAP[int(ranked_indices[1])]

            # Compute estimated purchase conversion probability
            # Higher weight on Quick Buyer, Brand Loyal, and pickup/return ratios
            conversion_prob = float(
                0.4 * prob_dict.get("BRAND_LOYAL", 0.0)
                + 0.35 * prob_dict.get("QUICK_BUYER", 0.0)
                + 0.25 * prob_dict.get("IMPULSE_BUYER", 0.0)
                + 0.15 * prob_dict.get("COMPARISON_SHOPPER", 0.0)
                + 0.05 * prob_dict.get("EXPLORER", 0.0)
            )
            conversion_prob = max(0.0, min(1.0, conversion_prob))

            return ShopperClassification(
                track_id=track_id,
                session_id=session_id,
                primary_segment=primary_segment,
                confidence=primary_prob,
                secondary_segment=secondary_segment,
                feature_vector=feature_vector,
                probabilities=prob_dict,
                conversion_probability=conversion_prob,
                model_type="xgboost",
            )
        except Exception as e:
            logger.error(f"XGBoost classification failed: {e}")
            return None
