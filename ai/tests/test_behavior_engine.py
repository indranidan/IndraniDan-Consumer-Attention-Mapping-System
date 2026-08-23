"""
Integration Test — Module 6 Behavior Engine
===============================================
Feeds synthetic M3/M4/M5 data and validates the full result document.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.behavior_analysis.engine import Module6BehaviorEngine


def _make_synthetic_data():
    """Create synthetic Module 3/4/5 data with multiple shopper sessions."""
    m3_data = {
        "sessions": [
            {
                "tracking_id": 1, "session_id": "sess_1",
                "start_time": 0.0, "end_time": 60.0, "entry_time": 0.0,
                "status": "completed",
                "zones_visited": ["Entrance", "Aisle 1", "Aisle 2", "Aisle 3"],
                "zone_transitions": [
                    {"zone": "Entrance", "enter_time": 0.0, "duration": 3.0},
                    {"zone": "Aisle 1", "enter_time": 3.0, "duration": 20.0},
                    {"zone": "Aisle 2", "enter_time": 23.0, "duration": 15.0},
                    {"zone": "Aisle 3", "enter_time": 40.0, "duration": 15.0},
                ],
            },
            {
                "tracking_id": 2, "session_id": "sess_2",
                "start_time": 5.0, "end_time": 18.0, "entry_time": 5.0,
                "status": "completed",
                "zones_visited": ["Entrance", "Aisle 1"],
                "zone_transitions": [
                    {"zone": "Entrance", "enter_time": 5.0, "duration": 1.0},
                    {"zone": "Aisle 1", "enter_time": 6.0, "duration": 10.0},
                ],
            },
            {
                "tracking_id": 3, "session_id": "sess_3",
                "start_time": 10.0, "end_time": 45.0, "entry_time": 10.0,
                "status": "completed",
                "zones_visited": ["Entrance", "Aisle 2"],
                "zone_transitions": [
                    {"zone": "Entrance", "enter_time": 10.0, "duration": 2.0},
                    {"zone": "Aisle 2", "enter_time": 12.0, "duration": 30.0},
                ],
            },
        ],
        "shoppers": [
            {"tracking_id": 1, "path": [{"x": 0, "y": 0}, {"x": 10, "y": 5}, {"x": 30, "y": 10}, {"x": 60, "y": 20}, {"x": 100, "y": 30}]},
            {"tracking_id": 2, "path": [{"x": 0, "y": 0}, {"x": 50, "y": 0}, {"x": 100, "y": 0}]},
            {"tracking_id": 3, "path": [{"x": 0, "y": 0}, {"x": 20, "y": 30}, {"x": 50, "y": 10}]},
        ],
    }

    m4_data = {
        "attention_events": [
            {"track_id": 1, "target_id": "shelf_A", "start_time": 5.0, "duration_seconds": 4.0},
            {"track_id": 1, "target_id": "shelf_B", "start_time": 10.0, "duration_seconds": 3.0},
            {"track_id": 1, "target_id": "shelf_A", "start_time": 15.0, "duration_seconds": 2.0},
            {"track_id": 3, "target_id": "shelf_B", "start_time": 15.0, "duration_seconds": 8.0},
        ],
    }

    m5_data = {
        "events": [
            {"track_id": 1, "event_type": "PRODUCT_VIEWED", "product_name": "Coffee", "timestamp": 6.0, "duration_seconds": 2.0},
            {"track_id": 1, "event_type": "PRODUCT_PICKED_UP", "product_name": "Coffee", "timestamp": 9.0, "duration_seconds": 0.5},
            {"track_id": 2, "event_type": "PRODUCT_PICKED_UP", "product_name": "Tea", "timestamp": 8.0, "duration_seconds": 0.3},
            {"track_id": 3, "event_type": "PRODUCT_VIEWED", "product_name": "Coffee", "timestamp": 20.0, "duration_seconds": 5.0},
            {"track_id": 3, "event_type": "PRODUCT_PICKED_UP", "product_name": "Coffee", "timestamp": 26.0, "duration_seconds": 0.5},
            {"track_id": 3, "event_type": "PRODUCT_RETURNED", "product_name": "Coffee", "timestamp": 30.0, "duration_seconds": 0.3},
        ],
    }

    return m3_data, m4_data, m5_data


def test_engine_full_pipeline():
    m3, m4, m5 = _make_synthetic_data()
    engine = Module6BehaviorEngine()
    result = engine.analyze(m3, m4, m5, store_id="store_1", camera_id="cam_1", job_id="job_001")

    # Validate top-level keys
    required_keys = ["job_id", "store_id", "camera_id", "summary", "shopper_segments",
                     "journeys", "zone_transitions", "funnel", "friction_points", "product_preferences"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"

    # Summary
    summary = result["summary"]
    assert summary["total_sessions"] == 3
    assert sum(summary["segment_counts"].values()) == 3
    print(f"[PASS] Summary: {summary}")

    # Segments
    assert len(result["shopper_segments"]) == 3
    for seg in result["shopper_segments"]:
        assert "primary_segment" in seg
        assert "confidence" in seg
        assert seg["confidence"] > 0
    print(f"[PASS] Segments: {[s['primary_segment'] for s in result['shopper_segments']]}")

    # Journeys
    assert len(result["journeys"]) == 3
    for j in result["journeys"]:
        assert "timeline" in j
        assert len(j["timeline"]) > 0
    print(f"[PASS] Journeys: {[len(j['timeline']) for j in result['journeys']]} events each")

    # Transitions
    assert "zones" in result["zone_transitions"]
    assert "matrix" in result["zone_transitions"]
    print(f"[PASS] Transitions: {len(result['zone_transitions']['zones'])} zones")

    # Funnel
    assert "stages" in result["funnel"]
    assert result["funnel"]["total_shoppers"] == 3
    print(f"[PASS] Funnel: {len(result['funnel']['stages'])} stages")

    # Product preferences
    assert isinstance(result["product_preferences"], list)
    print(f"[PASS] Product preferences: {len(result['product_preferences'])} products")

    print(f"\n[OK] Module 6 engine integration test passed - all {len(required_keys)} result keys present")


def test_engine_empty_data():
    engine = Module6BehaviorEngine()
    result = engine.analyze(
        m3_data={"sessions": [], "shoppers": []},
        m4_data={"attention_events": []},
        m5_data={"events": []},
        job_id="empty_job",
    )
    assert result["summary"]["total_sessions"] == 0
    assert result["shopper_segments"] == []
    assert result["journeys"] == []
    assert result["summary"]["average_journey_duration_sec"] == 0.0


def test_engine_fallback_tracks():
    engine = Module6BehaviorEngine()
    result = engine.analyze(
        m3_data=None,
        m4_data={"attention_events": [{"track_id": 10, "target_id": "shelf_1", "start_time": 1.0, "duration_seconds": 2.0}]},
        m5_data={"events": [{"track_id": 10, "product_name": "Soda", "event_type": "PRODUCT_PICKED_UP", "timestamp": 2.0}]},
        job_id="fallback_job",
    )
    assert result["summary"]["total_sessions"] == 1
    assert len(result["shopper_segments"]) == 1
    assert result["shopper_segments"][0]["track_id"] == 10


def test_engine_real_pipeline_formats():
    """Test engine with dictionary paths and null timestamps from real tracking pipeline."""
    engine = Module6BehaviorEngine()
    m3_data = {
        "sessions": [
            {
                "session_id": "session_001",
                "tracking_id": 1,
                "start_time": 0.153,
                "end_time": 19.476,
                "entry_time": None,
                "exit_time": None,
                "status": "track_lost",
                "zones_visited": ["Entrance"],
                "zone_transitions": [],
            }
        ],
        "paths": {
            "1": [
                {"frame": 2, "timestamp": 0.153, "x": 902, "y": 431},
                {"frame": 3, "timestamp": 0.229, "x": 905, "y": 435},
                {"frame": 4, "timestamp": 0.306, "x": 910, "y": 440},
            ]
        },
        "shoppers": [
            {"tracking_id": 1, "path": [{"x": 902, "y": 431}, {"x": 910, "y": 440}]}
        ],
    }
    m4_data = {"attention_events": []}
    m5_data = {"events": []}

    result = engine.analyze(m3_data, m4_data, m5_data, job_id="real_format_job")
    assert result["summary"]["total_sessions"] == 1
    assert len(result["journeys"]) == 1
    assert result["journeys"][0]["timeline"][0]["timestamp"] == 0.153
    assert result["journeys"][0]["timeline"][-1]["stage"] == "EXIT"


if __name__ == "__main__":
    test_engine_full_pipeline()
    test_engine_empty_data()
    test_engine_fallback_tracks()
    test_engine_real_pipeline_formats()


