"""
Module 3 Phase 3 — Movement Analysis Unit Tests
==================================================
All tests use synthetic tracking data (no video, no model, no GPU required).
Tests cover: zone geometry, path tracking, zone transitions, entry/exit
detection, duplicate prevention, track-lost handling, session generation,
journey generation, and traffic aggregation.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

# ── Ensure project root is in sys.path ────────────────────────
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Helper: create a temporary zones.json ─────────────────────
def _create_zones_config(tmp_dir: Path) -> Path:
    """Create a zones.json with known geometry for testing."""
    config = {
        "zones": [
            {
                "id": "zone_1",
                "name": "Zone A",
                "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
            },
            {
                "id": "zone_2",
                "name": "Zone B",
                "polygon": [[400, 100], [600, 100], [600, 300], [400, 300]],
            },
        ],
        "entry_regions": [
            {
                "id": "entry_1",
                "name": "Main Entry",
                "polygon": [[0, 0], [50, 0], [50, 200], [0, 200]],
            },
        ],
        "exit_regions": [
            {
                "id": "exit_1",
                "name": "Main Exit",
                "polygon": [[700, 0], [750, 0], [750, 200], [700, 200]],
            },
        ],
    }
    config_path = tmp_dir / "zones.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    return config_path


# ==================================================================
# TEST 1: Point inside zone
# ==================================================================
class TestPointInsideZone:
    def test_point_inside_rectangular_zone(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)

        # Point (200, 200) is inside zone_1 ([100,100] to [300,300])
        zones = zm.get_zones_for_point(200, 200)
        assert "zone_1" in zones

    def test_point_on_boundary(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)

        # Point on boundary should be inside (cv2 pointPolygonTest returns 0)
        zones = zm.get_zones_for_point(100, 100)
        assert "zone_1" in zones


# ==================================================================
# TEST 2: Point outside zone
# ==================================================================
class TestPointOutsideZone:
    def test_point_outside_all_zones(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)

        # Point (350, 200) is between zone_1 and zone_2
        zones = zm.get_zones_for_point(350, 200)
        assert len(zones) == 0

    def test_point_far_outside(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)

        zones = zm.get_zones_for_point(900, 900)
        assert len(zones) == 0


# ==================================================================
# TEST 3: Invalid polygon
# ==================================================================
class TestInvalidPolygon:
    def test_polygon_with_fewer_than_3_vertices(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config = {
            "zones": [
                {"id": "bad_zone", "name": "Bad", "polygon": [[0, 0], [10, 10]]}
            ],
            "entry_regions": [],
            "exit_regions": [],
        }
        config_path = tmp_path / "bad_zones.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        with pytest.raises(ValueError, match="at least 3 vertices"):
            ZoneManager(config_path)

    def test_missing_polygon_field(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config = {
            "zones": [{"id": "no_poly", "name": "No Polygon"}],
            "entry_regions": [],
            "exit_regions": [],
        }
        config_path = tmp_path / "no_poly.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        with pytest.raises(ValueError, match="Missing 'polygon'"):
            ZoneManager(config_path)


# ==================================================================
# TEST 4: Zone transition detection
# ==================================================================
class TestZoneTransition:
    def test_transition_zone_a_to_zone_b(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.zone_tracker import ZoneTracker

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        zt = ZoneTracker(zone_manager=zm)

        # Shopper enters zone_1
        zt.update(track_id=1, frame=1, timestamp=0.1, center_x=200, center_y=200)
        state = zt.get_state(1)
        assert "zone_1" in state.current_zones

        # Shopper moves to gap between zones
        zt.update(track_id=1, frame=2, timestamp=0.2, center_x=350, center_y=200)
        assert "zone_1" not in state.current_zones

        # Shopper enters zone_2
        zt.update(track_id=1, frame=3, timestamp=0.3, center_x=500, center_y=200)
        assert "zone_2" in state.current_zones

        # Check transition sequence
        transitions = state.get_transition_sequence()
        assert transitions == ["zone_1", "zone_2"]


# ==================================================================
# TEST 5: Entry detection
# ==================================================================
class TestEntryDetection:
    def test_entry_detected(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        monitor = EntryExitMonitor(zone_manager=zm)

        # Shopper at entry region (25, 100)
        event = monitor.update(track_id=1, frame=1, timestamp=0.1, center_x=25, center_y=100)
        assert event is not None
        assert event.event_type == "entry"
        assert monitor.total_entries == 1


# ==================================================================
# TEST 6: Exit detection
# ==================================================================
class TestExitDetection:
    def test_exit_detected(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        monitor = EntryExitMonitor(zone_manager=zm)

        # First enter
        monitor.update(track_id=1, frame=1, timestamp=0.1, center_x=25, center_y=100)

        # Then exit at exit region (725, 100)
        event = monitor.update(track_id=1, frame=10, timestamp=1.0, center_x=725, center_y=100)
        assert event is not None
        assert event.event_type == "exit"
        assert monitor.total_exits == 1


# ==================================================================
# TEST 7: Duplicate entry prevention
# ==================================================================
class TestDuplicateEntryPrevention:
    def test_same_track_does_not_reenter(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        monitor = EntryExitMonitor(zone_manager=zm)

        # First entry
        event1 = monitor.update(track_id=1, frame=1, timestamp=0.1, center_x=25, center_y=100)
        assert event1 is not None

        # Second pass through entry — should NOT count again
        event2 = monitor.update(track_id=1, frame=5, timestamp=0.5, center_x=25, center_y=100)
        assert event2 is None
        assert monitor.total_entries == 1


# ==================================================================
# TEST 8: Track-lost handling
# ==================================================================
class TestTrackLostHandling:
    def test_track_lost_without_exit(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        monitor = EntryExitMonitor(zone_manager=zm)

        # Enter but never exit
        monitor.update(track_id=1, frame=1, timestamp=0.1, center_x=25, center_y=100)

        # Mark as lost
        monitor.mark_track_lost(track_id=1, frame=50, timestamp=5.0)

        assert monitor.is_track_lost(1)
        assert not monitor.has_exited(1)
        assert monitor.total_exits == 0


# ==================================================================
# TEST 9: Session generation
# ==================================================================
class TestSessionGeneration:
    def test_session_created_and_finalized(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
        from ai.movement_analysis.path_tracker import PathTracker
        from ai.movement_analysis.session_manager import SessionManager
        from ai.movement_analysis.zone_tracker import ZoneTracker

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        pt = PathTracker(history_length=50)
        zt = ZoneTracker(zone_manager=zm)
        eem = EntryExitMonitor(zone_manager=zm)
        sm = SessionManager()

        # Simulate a shopper journey
        # Enter
        eem.update(track_id=1, frame=1, timestamp=0.1, center_x=25, center_y=100)
        sm.update_session(1, 1, 0.1, 0.9)
        pt.update(1, 1, 0.1, 25, 100)

        # Move to zone_1
        zt.update(1, 5, 0.5, 200, 200)
        sm.update_session(1, 5, 0.5, 0.88)
        pt.update(1, 5, 0.5, 200, 200)

        # Exit
        eem.update(track_id=1, frame=20, timestamp=2.0, center_x=725, center_y=100)
        sm.update_session(1, 20, 2.0, 0.85)

        # Finalize
        sm.finalize_all(pt, zt, eem)

        sessions = sm.get_all_sessions()
        assert len(sessions) == 1

        s = sessions[0]
        assert s.tracking_id == 1
        assert s.status == "completed"
        assert s.entry_time is not None
        assert s.exit_time is not None


# ==================================================================
# TEST 10: Shopper journey generation
# ==================================================================
class TestShopperJourneyGeneration:
    def test_journey_has_chronological_events(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
        from ai.movement_analysis.path_tracker import PathTracker
        from ai.movement_analysis.session_manager import SessionManager
        from ai.movement_analysis.zone_tracker import ZoneTracker

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        pt = PathTracker(history_length=50)
        zt = ZoneTracker(zone_manager=zm)
        eem = EntryExitMonitor(zone_manager=zm)
        sm = SessionManager()

        # Enter
        eem.update(1, 1, 0.1, 25, 100)
        sm.update_session(1, 1, 0.1, 0.9)
        pt.update(1, 1, 0.1, 25, 100)

        # Zone A
        zt.update(1, 5, 0.5, 200, 200)
        sm.update_session(1, 5, 0.5, 0.88)

        # Zone B
        zt.update(1, 10, 1.0, 350, 200)  # gap
        zt.update(1, 15, 1.5, 500, 200)
        sm.update_session(1, 15, 1.5, 0.87)

        # Exit
        eem.update(1, 20, 2.0, 725, 100)
        sm.update_session(1, 20, 2.0, 0.85)

        sm.finalize_all(pt, zt, eem)

        session = sm.get_session(1)
        journey = session.journey

        # Should have: entry, zone_1, zone_2, exit
        assert len(journey) >= 3
        assert journey[0]["event"] == "entry"
        assert journey[-1]["event"] == "exit"

        # Timestamps should be chronological
        timestamps = [e["timestamp"] for e in journey]
        assert timestamps == sorted(timestamps)


# ==================================================================
# TEST 11: Traffic aggregation
# ==================================================================
class TestTrafficAggregation:
    def test_zone_visitor_counts(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager
        from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
        from ai.movement_analysis.path_tracker import PathTracker
        from ai.movement_analysis.session_manager import SessionManager
        from ai.movement_analysis.traffic_analyzer import TrafficAnalyzer
        from ai.movement_analysis.zone_tracker import ZoneTracker

        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        zt = ZoneTracker(zone_manager=zm)
        eem = EntryExitMonitor(zone_manager=zm)
        sm = SessionManager()

        # Shopper 1 visits zone_1
        zt.update(1, 1, 0.1, 200, 200)
        sm.update_session(1, 1, 0.1, 0.9)

        # Shopper 2 visits zone_1 and zone_2
        zt.update(2, 1, 0.1, 200, 200)
        sm.update_session(2, 1, 0.1, 0.85)
        zt.update(2, 5, 0.5, 350, 200)  # gap
        zt.update(2, 10, 1.0, 500, 200)
        sm.update_session(2, 10, 1.0, 0.86)

        # Shopper 3 visits zone_2 only
        zt.update(3, 1, 0.1, 500, 200)
        sm.update_session(3, 1, 0.1, 0.82)

        pt = PathTracker()
        ta = TrafficAnalyzer(
            zone_manager=zm, zone_tracker=zt,
            entry_exit_monitor=eem, session_manager=sm,
        )
        ta.record_frame_active_count(3)
        ta.record_frame_active_count(2)
        ta.record_frame_active_count(1)

        stats = ta.generate_stats()

        assert stats["total_unique_shoppers"] == 3
        assert stats["max_simultaneous_shoppers"] == 3

        # Zone 1 should have 2 unique visitors (shopper 1 and 2)
        zone_stats = {zs["zone_id"]: zs for zs in stats["zone_statistics"]}
        assert zone_stats["zone_1"]["unique_visitors"] == 2
        assert zone_stats["zone_2"]["unique_visitors"] == 2  # shoppers 2 and 3


# ==================================================================
# Additional: Path tracker test
# ==================================================================
class TestPathTracker:
    def test_path_records_positions(self):
        from ai.movement_analysis.path_tracker import PathTracker

        pt = PathTracker(history_length=50)
        pt.update(1, 1, 0.1, 100, 200)
        pt.update(1, 2, 0.2, 110, 210)
        pt.update(1, 3, 0.3, 120, 220)

        path = pt.get_path(1)
        assert path is not None
        assert path.total_points == 3

        full = path.get_full_path()
        assert full[0].x == 100
        assert full[2].x == 120

        vis = path.get_visualization_points()
        assert len(vis) == 3
        assert vis[0] == (100, 200)


# ==================================================================
# TEST: Normalized Zone Coordinate Scaling
# ==================================================================
class TestNormalizedZoneScaling:
    def test_normalized_coordinates_scale_to_frame_size(self, tmp_path):
        from ai.movement_analysis.zone_manager import ZoneManager

        config = {
            "zones": [
                {
                    "id": "norm_zone_1",
                    "name": "Normalized Zone 1",
                    "polygon": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]],
                }
            ],
            "entry_regions": [],
            "exit_regions": [],
        }
        config_path = tmp_path / "norm_zones.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Initialize with frame_size=(1000, 1000)
        zm = ZoneManager(config_path, frame_size=(1000, 1000))
        z1 = zm.zones["norm_zone_1"]
        assert z1.is_normalized is True
        assert z1.polygon == [(100, 100), (500, 100), (500, 500), (100, 500)]

        # Point (250, 250) is inside
        assert "norm_zone_1" in zm.get_zones_for_point(250, 250)
        # Point (600, 600) is outside
        assert "norm_zone_1" not in zm.get_zones_for_point(600, 600)

        # Scale to a different resolution (1920, 1080)
        zm.scale_to_frame_size(1920, 1080)
        assert z1.polygon == [(192, 108), (960, 108), (960, 540), (192, 540)]
        assert "norm_zone_1" in zm.get_zones_for_point(500, 300)

