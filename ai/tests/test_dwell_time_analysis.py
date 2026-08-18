"""
Module 3 Phase 4 — Dwell-Time Analytics Unit Tests
=====================================================
All tests use synthetic tracking data (no video, no model, no GPU required).
Tests cover:
  1. Basic dwell-time calculation (entry time, exit time, duration)
  2. Multiple zone visits by a single shopper
  3. Repeated visits to the same zone by a single shopper
  4. Session duration calculation for completed sessions
  5. Track-lost handling (status = "track_lost", observed vs completed)
  6. Short tracking gap tolerance (gap <= tolerance vs gap > tolerance)
  7. Zone dwell aggregation (unique shoppers, min/max/avg/median/total)
  8. Dwell-time distribution bucket grouping
  9. Overlapping zone handling (shopper in multiple zones simultaneously)
  10. Empty detection input handling
"""

import json
from pathlib import Path
import sys

import pytest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.dwell_time_analysis.dwell_tracker import DwellTracker, DwellEvent
from ai.dwell_time_analysis.dwell_aggregator import DwellAggregator
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.session_manager import SessionManager


# ── Helper: create a temporary zones.json ─────────────────────
def _create_zones_config(tmp_dir: Path) -> Path:
    """Create a zones.json with known geometry for testing."""
    config = {
        "zones": [
            {
                "id": "zone_1",
                "name": "Beverage Section",
                "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
            },
            {
                "id": "zone_2",
                "name": "Snacks Aisle",
                "polygon": [[400, 100], [600, 100], [600, 300], [400, 300]],
            },
            {
                "id": "zone_overlap",
                "name": "Overlap Zone",
                "polygon": [[200, 100], [500, 100], [500, 300], [200, 300]],
            },
        ],
        "entry_regions": [],
        "exit_regions": [],
    }
    config_path = tmp_dir / "zones.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    return config_path


# ==================================================================
# TEST 1: Basic dwell calculation
# ==================================================================
class TestBasicDwellCalculation:
    def test_entry_at_10_exit_at_42(self):
        """Entry at 10.0s (frame 300), Exit at 42.0s (frame 1260) -> Dwell = 32.0s."""
        dt = DwellTracker(gap_tolerance=15)
        zone_names = {"zone_1": "Beverage Section"}

        # Entry at frame 300 (10.0s)
        dt.update(
            track_id=1, frame=300, timestamp=10.0,
            current_zone_ids=["zone_1"], zone_names=zone_names, confidence=0.90,
        )

        # Presence update at frame 1260 (42.0s)
        dt.update(
            track_id=1, frame=1260, timestamp=42.0,
            current_zone_ids=["zone_1"], zone_names=zone_names, confidence=0.88,
        )

        # Exit at frame 1280 (42.667s) - gap > 15
        dt.update(
            track_id=1, frame=1280, timestamp=42.667,
            current_zone_ids=[], zone_names=zone_names, confidence=0.85,
        )

        state = dt.get_state(1)
        assert len(state.completed_visits) == 1
        visit = state.completed_visits[0]
        assert visit.zone_id == "zone_1"
        assert visit.entry_time == 10.0
        assert visit.status == "completed"
        assert visit.dwell_seconds is not None
        assert abs(visit.dwell_seconds - 32.0) < 1.0


# ==================================================================
# TEST 2: Multiple zone visits
# ==================================================================
class TestMultipleZoneVisits:
    def test_shopper_visits_zone_a_then_zone_b(self):
        dt = DwellTracker(gap_tolerance=15)
        zone_names = {"zone_1": "Beverage Section", "zone_2": "Snacks Aisle"}

        # Visit Zone 1
        dt.update(1, 10, 1.0, ["zone_1"], zone_names, 0.90)
        dt.update(1, 100, 10.0, ["zone_1"], zone_names, 0.88)

        # Move to Zone 2 (exit Zone 1 via gap tolerance)
        for f in range(120, 150):
            ts = f / 10.0
            dt.update(1, f, ts, ["zone_2"], zone_names, 0.87)

        events = dt.get_state(1).get_all_events()
        zone_ids = [e.zone_id for e in events]
        assert "zone_1" in zone_ids
        assert "zone_2" in zone_ids


# ==================================================================
# TEST 3: Repeated visits to same zone
# ==================================================================
class TestRepeatedZoneVisit:
    def test_two_separate_visits_to_same_zone(self):
        dt = DwellTracker(gap_tolerance=10)
        zone_names = {"zone_1": "Beverage Section"}

        # Visit 1
        dt.update(1, 10, 1.0, ["zone_1"], zone_names, 0.9)
        dt.update(1, 20, 2.0, ["zone_1"], zone_names, 0.9)

        # Leave zone for 20 frames (> gap_tolerance=10)
        dt.update(1, 50, 5.0, [], zone_names, 0.9)

        # Visit 2 (re-enter zone_1)
        dt.update(1, 60, 6.0, ["zone_1"], zone_names, 0.9)
        dt.update(1, 80, 8.0, ["zone_1"], zone_names, 0.9)

        events = dt.get_state(1).get_all_events()
        zone_1_events = [e for e in events if e.zone_id == "zone_1"]
        assert len(zone_1_events) == 2
        assert zone_1_events[0].visit_number == 1
        assert zone_1_events[1].visit_number == 2


# ==================================================================
# TEST 4: Session duration
# ==================================================================
class TestSessionDuration:
    def test_session_duration_from_session_manager(self):
        sm = SessionManager()
        sm.update_session(1, 1, 0.0, 0.9)
        sm.update_session(1, 100, 10.0, 0.85)

        s = sm.get_session(1)
        assert s is not None
        assert s.start_time == 0.0
        assert s.end_time == 10.0
        assert (s.end_time - s.start_time) == 10.0


# ==================================================================
# TEST 5: Track-lost handling
# ==================================================================
class TestTrackLostHandling:
    def test_track_lost_marks_events_as_track_lost(self):
        dt = DwellTracker(gap_tolerance=15)
        zone_names = {"zone_1": "Beverage Section"}

        # Enter zone_1
        dt.update(1, 10, 1.0, ["zone_1"], zone_names, 0.9)

        # Disappear without explicit exit
        closed_events = dt.handle_lost_track(1, 50, 5.0)

        assert len(closed_events) == 1
        assert closed_events[0].status == "track_lost"
        assert closed_events[0].exit_time == 5.0
        assert closed_events[0].dwell_seconds == 4.0


# ==================================================================
# TEST 6: Short tracking gaps tolerance
# ==================================================================
class TestShortTrackingGaps:
    def test_gap_within_tolerance_maintains_visit(self):
        dt = DwellTracker(gap_tolerance=15)
        zone_names = {"zone_1": "Beverage Section"}

        # Enter zone_1
        dt.update(1, 10, 1.0, ["zone_1"], zone_names, 0.9)

        # Missing for 10 frames (<= 15)
        dt.update(1, 20, 2.0, [], zone_names, 0.9)

        # Re-appear in zone_1 at frame 22
        dt.update(1, 22, 2.2, ["zone_1"], zone_names, 0.9)

        # Should still be in active_visits (single visit)
        state = dt.get_state(1)
        assert "zone_1" in state.active_visits
        assert len(state.completed_visits) == 0

    def test_gap_exceeding_tolerance_closes_visit(self):
        dt = DwellTracker(gap_tolerance=15)
        zone_names = {"zone_1": "Beverage Section"}

        # Enter zone_1
        dt.update(1, 10, 1.0, ["zone_1"], zone_names, 0.9)

        # Missing for 20 frames (> 15)
        dt.update(1, 35, 3.5, [], zone_names, 0.9)

        # Active visit closed
        state = dt.get_state(1)
        assert "zone_1" not in state.active_visits
        assert len(state.completed_visits) == 1


# ==================================================================
# TEST 7: Dwell Aggregation
# ==================================================================
class TestDwellAggregation:
    def test_zone_summaries_calculation(self, tmp_path):
        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)

        dt = DwellTracker(gap_tolerance=5)
        zone_names = {z.id: z.name for z in zm.get_all_zones()}

        # Shopper 1: 10s in zone_1
        dt.update(1, 1, 0.0, ["zone_1"], zone_names, 0.9)
        dt.update(1, 100, 10.0, ["zone_1"], zone_names, 0.9)
        dt.update(1, 120, 12.0, [], zone_names, 0.9)

        # Shopper 2: 20s in zone_1
        dt.update(2, 1, 0.0, ["zone_1"], zone_names, 0.85)
        dt.update(2, 200, 20.0, ["zone_1"], zone_names, 0.85)
        dt.update(2, 220, 22.0, [], zone_names, 0.85)

        agg = DwellAggregator()
        summaries = agg.aggregate_zones(dt, zm)

        z1_summary = next(s for s in summaries if s.zone_id == "zone_1")
        assert z1_summary.unique_shoppers == 2
        assert z1_summary.total_visits == 2
        assert z1_summary.min_dwell_seconds >= 9.0
        assert z1_summary.max_dwell_seconds >= 19.0
        assert z1_summary.average_dwell_seconds > 0.0


# ==================================================================
# TEST 8: Dwell Distribution
# ==================================================================
class TestDwellDistribution:
    def test_bucket_counting(self):
        dt = DwellTracker(gap_tolerance=5)
        zone_names = {"z1": "Zone 1"}

        # 5s visit (0-10s bucket)
        dt.update(1, 1, 0.0, ["z1"], zone_names, 0.9)
        dt.update(1, 50, 5.0, ["z1"], zone_names, 0.9)
        dt.update(1, 60, 6.0, [], zone_names, 0.9)

        # 45s visit (30-60s bucket)
        dt.update(2, 1, 0.0, ["z1"], zone_names, 0.9)
        dt.update(2, 450, 45.0, ["z1"], zone_names, 0.9)
        dt.update(2, 460, 46.0, [], zone_names, 0.9)

        agg = DwellAggregator()
        dist = agg.compute_distribution(dt, [10, 30, 60, 120])

        assert len(dist.buckets) == 5  # 0-10, 10-30, 30-60, 60-120, 120+
        b0_10 = next(b for b in dist.buckets if b.label == "0–10s")
        b30_60 = next(b for b in dist.buckets if b.label == "30–60s")

        assert b0_10.visit_count == 1
        assert b30_60.visit_count == 1


# ==================================================================
# TEST 9: Overlapping zones
# ==================================================================
class TestOverlappingZones:
    def test_shopper_in_overlapping_zones(self):
        dt = DwellTracker(gap_tolerance=10)
        zone_names = {"zone_1": "Zone A", "zone_overlap": "Overlap Zone"}

        # Shopper enters both zone_1 and zone_overlap simultaneously
        dt.update(1, 10, 1.0, ["zone_1", "zone_overlap"], zone_names, 0.9)
        dt.update(1, 50, 5.0, ["zone_1", "zone_overlap"], zone_names, 0.9)

        state = dt.get_state(1)
        active_ids = state.get_active_zone_ids()
        assert "zone_1" in active_ids
        assert "zone_overlap" in active_ids
        assert len(active_ids) == 2


# ==================================================================
# TEST 10: Empty detection input
# ==================================================================
class TestEmptyDetectionInput:
    def test_no_tracks_processed_gracefully(self, tmp_path):
        config_path = _create_zones_config(tmp_path)
        zm = ZoneManager(config_path)
        sm = SessionManager()

        dt = DwellTracker()
        dt.close_remaining_visits(frame=100, timestamp=10.0)

        agg = DwellAggregator()
        zone_summaries = agg.aggregate_zones(dt, zm)
        shopper_summaries = agg.aggregate_shoppers(dt, sm)
        dist = agg.compute_distribution(dt, [10, 30, 60])

        assert len(zone_summaries) == 3
        assert len(shopper_summaries) == 0
        assert dist.total_visits_counted == 0
