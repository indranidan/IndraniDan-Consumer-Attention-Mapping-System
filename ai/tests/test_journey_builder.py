"""
Unit Tests — Journey Builder
================================
Tests complete and incomplete journey reconstruction.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.behavior_analysis.journey_builder import JourneyBuilder


def test_complete_journey():
    session = {
        "tracking_id": 1, "session_id": "sess_1",
        "start_time": 0.0, "end_time": 30.0, "entry_time": 0.5,
        "status": "completed",
        "zones_visited": ["Entrance", "Aisle 1", "Checkout"],
        "zone_transitions": [
            {"zone": "Entrance", "enter_time": 0.5, "duration": 2.0},
            {"zone": "Aisle 1", "enter_time": 3.0, "duration": 20.0},
            {"zone": "Checkout", "enter_time": 25.0, "duration": 5.0},
        ],
        "journey": [],
    }
    m4 = {"attention_events": [
        {"track_id": 1, "target_id": "shelf_A", "start_time": 5.0, "duration_seconds": 4.0},
    ]}
    m5 = {"events": [
        {"track_id": 1, "event_type": "PRODUCT_PICKED_UP", "product_name": "Coffee", "timestamp": 10.0, "duration_seconds": 1.0},
    ]}

    result = JourneyBuilder().build_journey(session, None, m4, m5)
    assert result["status"] == "complete"
    stages = [e["stage"] for e in result["timeline"]]
    assert "ENTRY" in stages
    assert "EXIT" in stages
    assert "SHELF_GAZE" in stages
    assert "PRODUCT_INTERACTION" in stages
    print(f"[PASS] Complete journey: {len(result['timeline'])} events, status={result['status']}")


def test_incomplete_journey():
    session = {
        "tracking_id": 2, "session_id": "sess_2",
        "start_time": 0.0, "end_time": None,
        "status": "track_lost",
        "zones_visited": ["Entrance", "Aisle 1"],
        "zone_transitions": [
            {"zone": "Entrance", "enter_time": 0.0, "duration": 1.5},
            {"zone": "Aisle 1", "enter_time": 2.0, "duration": 8.0},
        ],
        "journey": [],
    }

    result = JourneyBuilder().build_journey(session, None, None, None)
    assert result["status"] == "incomplete"
    stages = [e["stage"] for e in result["timeline"]]
    assert "ENTRY" in stages
    assert "EXIT" not in stages
    print(f"[PASS] Incomplete journey: {len(result['timeline'])} events, status={result['status']}")


if __name__ == "__main__":
    test_complete_journey()
    test_incomplete_journey()
    print("\nAll journey builder tests passed!")
