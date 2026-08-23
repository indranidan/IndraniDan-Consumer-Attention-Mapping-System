"""
Unit Tests — Behavioral Classifier
=====================================
Tests classification for each archetype and a boundary case.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.behavior_analysis.classifier import BehaviorClassifier
from ai.behavior_analysis.config import BehaviorConfig
from ai.behavior_analysis.models import BehaviorFeatureVector, ShopperArchetype


def test_explorer():
    fv = BehaviorFeatureVector(path_efficiency=0.25, dwell_to_transit_ratio=0.7, zone_breadth=4,
                                gaze_alternation_rate=0.5, pickup_to_return_ratio=0.5,
                                brand_concentration=0.3, promo_deviation_count=0)
    result = BehaviorClassifier().classify(fv, BehaviorConfig(), track_id=1)
    assert result.primary_segment == ShopperArchetype.EXPLORER, f"Expected EXPLORER, got {result.primary_segment}"
    assert result.confidence > 0.0
    print(f"[PASS] Explorer: {result.to_dict()}")


def test_quick_buyer():
    fv = BehaviorFeatureVector(path_efficiency=0.85, dwell_to_transit_ratio=0.15, zone_breadth=1,
                                gaze_alternation_rate=0.0, pickup_to_return_ratio=2.0,
                                brand_concentration=0.5, promo_deviation_count=0)
    result = BehaviorClassifier().classify(fv, BehaviorConfig(), track_id=2)
    assert result.primary_segment == ShopperArchetype.QUICK_BUYER, f"Expected QUICK_BUYER, got {result.primary_segment}"
    print(f"[PASS] Quick Buyer: {result.to_dict()}")


def test_comparison_shopper():
    fv = BehaviorFeatureVector(path_efficiency=0.5, dwell_to_transit_ratio=0.6, zone_breadth=2,
                                gaze_alternation_rate=3.5, pickup_to_return_ratio=0.5,
                                brand_concentration=0.4, promo_deviation_count=0)
    result = BehaviorClassifier().classify(fv, BehaviorConfig(), track_id=3)
    assert result.primary_segment == ShopperArchetype.COMPARISON_SHOPPER, f"Expected COMPARISON_SHOPPER, got {result.primary_segment}"
    print(f"[PASS] Comparison Shopper: {result.to_dict()}")


def test_impulse_buyer():
    fv = BehaviorFeatureVector(path_efficiency=0.5, dwell_to_transit_ratio=0.4, zone_breadth=2,
                                gaze_alternation_rate=0.3, pickup_to_return_ratio=1.5,
                                brand_concentration=0.4, promo_deviation_count=2)
    result = BehaviorClassifier().classify(fv, BehaviorConfig(), track_id=4)
    assert result.primary_segment == ShopperArchetype.IMPULSE_BUYER, f"Expected IMPULSE_BUYER, got {result.primary_segment}"
    print(f"[PASS] Impulse Buyer: {result.to_dict()}")


def test_brand_loyal():
    fv = BehaviorFeatureVector(path_efficiency=0.6, dwell_to_transit_ratio=0.3, zone_breadth=1,
                                gaze_alternation_rate=0.2, pickup_to_return_ratio=2.0,
                                brand_concentration=0.9, promo_deviation_count=0)
    result = BehaviorClassifier().classify(fv, BehaviorConfig(), track_id=5)
    assert result.primary_segment == ShopperArchetype.BRAND_LOYAL, f"Expected BRAND_LOYAL, got {result.primary_segment}"
    print(f"[PASS] Brand Loyal: {result.to_dict()}")


def test_ambiguous_boundary():
    """Session near the boundary between Explorer and Comparison Shopper."""
    fv = BehaviorFeatureVector(path_efficiency=0.38, dwell_to_transit_ratio=0.65, zone_breadth=3,
                                gaze_alternation_rate=2.1, pickup_to_return_ratio=0.8,
                                brand_concentration=0.35, promo_deviation_count=0)
    result = BehaviorClassifier().classify(fv, BehaviorConfig(), track_id=6)
    # Should classify but may have a secondary
    assert result.primary_segment in (ShopperArchetype.EXPLORER, ShopperArchetype.COMPARISON_SHOPPER)
    assert result.confidence > 0.0
    print(f"[PASS] Ambiguous boundary: primary={result.primary_segment.value}, "
          f"secondary={result.secondary_segment.value if result.secondary_segment else None}, "
          f"confidence={result.confidence:.4f}")


if __name__ == "__main__":
    test_explorer()
    test_quick_buyer()
    test_comparison_shopper()
    test_impulse_buyer()
    test_brand_loyal()
    test_ambiguous_boundary()
    print("\nAll classifier tests passed!")
