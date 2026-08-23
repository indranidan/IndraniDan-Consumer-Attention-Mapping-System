"""
Unit Tests — Behavioral Feature Extractor
============================================
Tests feature computation for normal sessions, missing M4, and missing M5.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.behavior_analysis.feature_extractor import BehaviorFeatureExtractor


def _make_session(track_id=1, zones=None, transitions=None, start=0.0, end=30.0, journey=None):
    return {
        "tracking_id": track_id,
        "session_id": f"sess_{track_id}",
        "start_time": start,
        "end_time": end,
        "zones_visited": zones or ["Zone A", "Zone B", "Zone C"],
        "zone_transitions": transitions or [
            {"zone": "Zone A", "duration": 8.0},
            {"zone": "Zone B", "duration": 6.0},
            {"zone": "Zone C", "duration": 4.0},
        ],
        "journey": journey or [],
        "status": "completed",
    }


def _make_m3_data(track_id=1, path=None):
    if path is None:
        path = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 20, "y": 10},
            {"x": 50, "y": 10},
            {"x": 100, "y": 0},
        ]
    return {
        "shoppers": [
            {"tracking_id": track_id, "path": path},
        ]
    }


def _make_m4_data(track_id=1):
    return {
        "attention_events": [
            {"track_id": track_id, "target_id": "shelf_A", "start_time": 2.0, "duration_seconds": 3.0},
            {"track_id": track_id, "target_id": "shelf_B", "start_time": 6.0, "duration_seconds": 2.0},
            {"track_id": track_id, "target_id": "shelf_A", "start_time": 9.0, "duration_seconds": 1.5},
        ]
    }


def _make_m5_data(track_id=1):
    return {
        "events": [
            {"track_id": track_id, "event_type": "PRODUCT_PICKED_UP", "product_name": "Brand X"},
            {"track_id": track_id, "event_type": "PRODUCT_RETURNED", "product_name": "Brand X"},
            {"track_id": track_id, "event_type": "PRODUCT_PICKED_UP", "product_name": "Brand Y"},
            {"track_id": track_id, "event_type": "PRODUCT_VIEWED", "product_name": "Brand X"},
        ]
    }


def test_normal_session():
    """Full session with all three modules available."""
    extractor = BehaviorFeatureExtractor()
    session = _make_session()
    fv = extractor.extract_features(session, _make_m3_data(), _make_m4_data(), _make_m5_data())

    assert fv.has_reduced_confidence is False
    assert 0.0 <= fv.path_efficiency <= 1.0
    assert fv.zone_breadth == 3
    assert fv.gaze_alternation_rate > 0.0
    assert fv.pickup_to_return_ratio > 0.0
    assert fv.brand_concentration > 0.0
    print(f"[PASS] Normal session: {fv.to_dict()}")


def test_missing_m4():
    """Session with no attention data — gaze features should be zero, reduced confidence."""
    extractor = BehaviorFeatureExtractor()
    session = _make_session()
    fv = extractor.extract_features(session, _make_m3_data(), None, _make_m5_data())

    assert fv.has_reduced_confidence is True
    assert fv.gaze_alternation_rate == 0.0
    assert fv.pickup_to_return_ratio > 0.0  # M5 still present
    print(f"[PASS] Missing M4: {fv.to_dict()}")


def test_missing_m5():
    """Session with no interaction data — interaction features should be zero."""
    extractor = BehaviorFeatureExtractor()
    session = _make_session()
    fv = extractor.extract_features(session, _make_m3_data(), _make_m4_data(), None)

    assert fv.has_reduced_confidence is True
    assert fv.pickup_to_return_ratio == 0.0
    assert fv.brand_concentration == 0.0
    assert fv.promo_deviation_count == 0
    assert fv.gaze_alternation_rate > 0.0  # M4 still present
    print(f"[PASS] Missing M5: {fv.to_dict()}")


if __name__ == "__main__":
    test_normal_session()
    test_missing_m4()
    test_missing_m5()
    print("\nAll feature extractor tests passed!")
