"""
Module 3 Phase 5 — Attention Analysis Unit Tests
====================================================
All tests use synthetic data (no video, no model, no GPU required).
Tests cover:
  1. Head-pose output validation
  2. Low-confidence handling
  3. Attention-direction classification
  4. Temporal smoothing
  5. Attention-region intersection
  6. Unknown target handling
  7. Attention event creation
  8. Attention duration calculation
  9. Repeated attention events
  10. Low-visibility handling
"""

import json
import math
from pathlib import Path
import sys

import pytest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.attention_analysis.attention_classifier import (
    AttentionClassifier,
    AttentionDirection,
    AttentionState,
)
from ai.attention_analysis.temporal_smoother import TemporalSmoother
from ai.attention_analysis.attention_tracker import AttentionTracker, AttentionEvent
from ai.attention_analysis.attention_region_manager import AttentionRegionManager
from ai.attention_analysis.head_pose_estimator import HeadPoseResult, NO_DETECTION


# ── Helper: create a temporary attention_regions.json ──────────
def _create_attention_regions(tmp_dir: Path) -> Path:
    """Create an attention_regions.json with known geometry."""
    config = {
        "regions": [
            {
                "id": "shelf_1",
                "name": "Beverage Shelf",
                "type": "shelf",
                "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
            },
            {
                "id": "shelf_2",
                "name": "Snacks Shelf",
                "type": "shelf",
                "polygon": [[400, 100], [600, 100], [600, 300], [400, 300]],
            },
            {
                "id": "shelf_3",
                "name": "Checkout Display",
                "type": "shelf",
                "polygon": [[100, 400], [300, 400], [300, 600], [100, 600]],
            },
        ]
    }
    config_path = tmp_dir / "attention_regions.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    return config_path


# ==================================================================
# TEST 1: Head-pose output validation
# ==================================================================
class TestHeadPoseOutputValidation:
    """Verify HeadPoseResult structure and value ranges."""

    def test_no_detection_sentinel_values(self):
        """NO_DETECTION should have face_detected=False and zero angles."""
        assert NO_DETECTION.face_detected is False
        assert NO_DETECTION.yaw == 0.0
        assert NO_DETECTION.pitch == 0.0
        assert NO_DETECTION.roll == 0.0
        assert NO_DETECTION.confidence == 0.0
        assert NO_DETECTION.detection_method == "head_orientation"

    def test_valid_head_pose_result_structure(self):
        """A valid HeadPoseResult should have all required fields."""
        result = HeadPoseResult(
            yaw=25.0, pitch=-10.0, roll=5.0,
            face_detected=True, confidence=0.85,
            face_bbox=(100, 50, 200, 150),
            nose_point=(150, 80),
            detection_method="head_orientation",
        )
        assert result.face_detected is True
        assert -90.0 <= result.yaw <= 90.0
        assert -90.0 <= result.pitch <= 90.0
        assert -90.0 <= result.roll <= 90.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.detection_method == "head_orientation"

    def test_head_pose_angles_within_range(self):
        """Verify yaw, pitch, roll are within valid degree ranges."""
        for yaw in [-90, -45, 0, 45, 90]:
            for pitch in [-90, -45, 0, 45, 90]:
                result = HeadPoseResult(
                    yaw=float(yaw), pitch=float(pitch), roll=0.0,
                    face_detected=True, confidence=0.8,
                    face_bbox=(0, 0, 100, 100), nose_point=(50, 50),
                    detection_method="head_orientation",
                )
                assert -90.0 <= result.yaw <= 90.0
                assert -90.0 <= result.pitch <= 90.0


# ==================================================================
# TEST 2: Low-confidence handling
# ==================================================================
class TestLowConfidenceHandling:
    """Below-threshold confidence should produce UNKNOWN."""

    def test_below_threshold_returns_unknown(self):
        """Confidence below threshold must return UNKNOWN direction and state."""
        classifier = AttentionClassifier()
        direction, state = classifier.classify(
            yaw=30.0, pitch=0.0,
            confidence=0.3, confidence_threshold=0.6,
        )
        assert direction == AttentionDirection.UNKNOWN
        assert state == AttentionState.UNKNOWN

    def test_at_threshold_returns_valid(self):
        """Confidence at exactly threshold should produce a valid direction."""
        classifier = AttentionClassifier()
        direction, state = classifier.classify(
            yaw=30.0, pitch=0.0,
            confidence=0.6, confidence_threshold=0.6,
        )
        assert direction == AttentionDirection.RIGHT
        assert state == AttentionState.ATTENDING

    def test_above_threshold_returns_valid(self):
        """Confidence above threshold should produce a valid direction."""
        classifier = AttentionClassifier()
        direction, state = classifier.classify(
            yaw=-25.0, pitch=0.0,
            confidence=0.9, confidence_threshold=0.6,
        )
        assert direction == AttentionDirection.LEFT
        assert state == AttentionState.ATTENDING

    def test_zero_confidence_returns_unknown(self):
        """Zero confidence should always return UNKNOWN."""
        classifier = AttentionClassifier()
        direction, state = classifier.classify(
            yaw=0.0, pitch=0.0,
            confidence=0.0, confidence_threshold=0.1,
        )
        assert direction == AttentionDirection.UNKNOWN
        assert state == AttentionState.UNKNOWN


# ==================================================================
# TEST 3: Attention-direction classification
# ==================================================================
class TestAttentionDirectionClassification:
    """Verify yaw/pitch → correct direction enum mapping."""

    def test_center_direction(self):
        classifier = AttentionClassifier(yaw_threshold=15.0, pitch_threshold=15.0)
        d, s = classifier.classify(yaw=0.0, pitch=0.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.CENTER

    def test_right_direction(self):
        classifier = AttentionClassifier(yaw_threshold=15.0)
        d, s = classifier.classify(yaw=25.0, pitch=0.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.RIGHT

    def test_left_direction(self):
        classifier = AttentionClassifier(yaw_threshold=15.0)
        d, s = classifier.classify(yaw=-25.0, pitch=0.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.LEFT

    def test_up_direction(self):
        classifier = AttentionClassifier(pitch_threshold=15.0)
        d, s = classifier.classify(yaw=0.0, pitch=25.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.UP

    def test_down_direction(self):
        classifier = AttentionClassifier(pitch_threshold=15.0)
        d, s = classifier.classify(yaw=0.0, pitch=-25.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.DOWN

    def test_yaw_priority_over_pitch(self):
        """Yaw should take priority for combined poses."""
        classifier = AttentionClassifier(yaw_threshold=15.0, pitch_threshold=15.0)
        d, s = classifier.classify(yaw=30.0, pitch=-30.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.RIGHT  # Yaw wins

    def test_boundary_yaw_is_center(self):
        """Yaw exactly at threshold should be CENTER."""
        classifier = AttentionClassifier(yaw_threshold=15.0)
        d, s = classifier.classify(yaw=15.0, pitch=0.0, confidence=0.9, confidence_threshold=0.5)
        assert d == AttentionDirection.CENTER

    def test_all_directions_are_attending(self):
        """All valid directions should produce ATTENDING state."""
        classifier = AttentionClassifier()
        for yaw, pitch in [(30, 0), (-30, 0), (0, 0), (0, 30), (0, -30)]:
            _, state = classifier.classify(
                yaw=float(yaw), pitch=float(pitch),
                confidence=0.9, confidence_threshold=0.5,
            )
            assert state == AttentionState.ATTENDING


# ==================================================================
# TEST 4: Temporal smoothing
# ==================================================================
class TestTemporalSmoothing:
    """Verify jittery inputs smooth to stable output."""

    def test_single_observation_passes_through(self):
        smoother = TemporalSmoother(window_size=5)
        d, c = smoother.update(1, AttentionDirection.RIGHT, 0.8)
        assert d == AttentionDirection.RIGHT

    def test_consistent_direction_stays_stable(self):
        smoother = TemporalSmoother(window_size=3)
        for _ in range(3):
            d, c = smoother.update(1, AttentionDirection.LEFT, 0.85)
        assert d == AttentionDirection.LEFT

    def test_jittery_input_smooths(self):
        """CENTER/RIGHT/CENTER/RIGHT/CENTER → CENTER wins (3 vs 2)."""
        smoother = TemporalSmoother(window_size=5)
        inputs = [
            AttentionDirection.CENTER,
            AttentionDirection.RIGHT,
            AttentionDirection.CENTER,
            AttentionDirection.RIGHT,
            AttentionDirection.CENTER,
        ]
        for d_in in inputs:
            result, _ = smoother.update(1, d_in, 0.8)
        assert result == AttentionDirection.CENTER

    def test_clear_majority_wins(self):
        """RIGHT/RIGHT/RIGHT/LEFT/CENTER → RIGHT wins clearly."""
        smoother = TemporalSmoother(window_size=5)
        inputs = [
            AttentionDirection.RIGHT,
            AttentionDirection.RIGHT,
            AttentionDirection.RIGHT,
            AttentionDirection.LEFT,
            AttentionDirection.CENTER,
        ]
        for d_in in inputs:
            result, _ = smoother.update(1, d_in, 0.8)
        assert result == AttentionDirection.RIGHT

    def test_tied_directions_return_unknown(self):
        """Equal counts of non-UNKNOWN directions → UNKNOWN."""
        smoother = TemporalSmoother(window_size=4)
        inputs = [
            AttentionDirection.LEFT,
            AttentionDirection.LEFT,
            AttentionDirection.RIGHT,
            AttentionDirection.RIGHT,
        ]
        for d_in in inputs:
            result, _ = smoother.update(1, d_in, 0.8)
        assert result == AttentionDirection.UNKNOWN

    def test_reset_clears_history(self):
        smoother = TemporalSmoother(window_size=3)
        for _ in range(3):
            smoother.update(1, AttentionDirection.LEFT, 0.8)
        smoother.reset(1)
        assert smoother.get_window_fill(1) == 0

    def test_independent_tracks(self):
        """Different track IDs should have independent smoothing."""
        smoother = TemporalSmoother(window_size=3)
        smoother.update(1, AttentionDirection.LEFT, 0.8)
        smoother.update(2, AttentionDirection.RIGHT, 0.7)
        assert smoother.get_window_fill(1) == 1
        assert smoother.get_window_fill(2) == 1

    def test_short_changes_preserved(self):
        """A legitimate direction change should appear after enough frames."""
        smoother = TemporalSmoother(window_size=3)
        # First 3: LEFT
        for _ in range(3):
            smoother.update(1, AttentionDirection.LEFT, 0.8)
        # Next 3: RIGHT
        for _ in range(3):
            result, _ = smoother.update(1, AttentionDirection.RIGHT, 0.8)
        assert result == AttentionDirection.RIGHT


# ==================================================================
# TEST 5: Attention-region intersection
# ==================================================================
class TestAttentionRegionIntersection:
    """Test ray-polygon intersection geometry."""

    def test_point_inside_region(self, tmp_path):
        config_path = _create_attention_regions(tmp_path)
        mgr = AttentionRegionManager(config_path=config_path)
        region = mgr.get_region("shelf_1")
        assert region is not None
        assert mgr.point_in_region(200, 200, region) is True

    def test_point_outside_region(self, tmp_path):
        config_path = _create_attention_regions(tmp_path)
        mgr = AttentionRegionManager(config_path=config_path)
        region = mgr.get_region("shelf_1")
        assert mgr.point_in_region(500, 500, region) is False

    def test_find_target_when_looking_at_region(self, tmp_path):
        """Head at (50, 200) looking RIGHT (yaw=30) should find shelf_1."""
        config_path = _create_attention_regions(tmp_path)
        mgr = AttentionRegionManager(config_path=config_path)
        target = mgr.find_attention_target(
            head_x=50, head_y=200, yaw=30.0, pitch=0.0, max_distance=500,
        )
        assert target is not None
        assert target.id == "shelf_1"

    def test_no_target_when_looking_away(self, tmp_path):
        """Head at (200, 200) looking LEFT (yaw=-80) with nothing to the left."""
        config_path = _create_attention_regions(tmp_path)
        mgr = AttentionRegionManager(config_path=config_path)
        target = mgr.find_attention_target(
            head_x=50, head_y=200, yaw=-80.0, pitch=0.0, max_distance=100,
        )
        assert target is None

    def test_region_loading(self, tmp_path):
        """All 3 regions should load correctly."""
        config_path = _create_attention_regions(tmp_path)
        mgr = AttentionRegionManager(config_path=config_path)
        assert len(mgr.get_all_regions()) == 3

    def test_invalid_polygon_raises(self, tmp_path):
        """Polygon with < 3 vertices should raise ValueError."""
        config = {
            "regions": [{
                "id": "bad", "name": "Bad", "type": "shelf",
                "polygon": [[0, 0], [100, 0]],
            }]
        }
        config_path = tmp_path / "bad_regions.json"
        with open(config_path, "w") as f:
            json.dump(config, f)
        with pytest.raises(ValueError, match="at least 3 vertices"):
            AttentionRegionManager(config_path=config_path)


# ==================================================================
# TEST 6: Unknown target handling
# ==================================================================
class TestUnknownTargetHandling:
    """No region hit should result in target=UNKNOWN."""

    def test_no_target_sets_unknown_in_tracker(self):
        tracker = AttentionTracker()
        tracker.update(
            track_id=1, frame=10, timestamp=1.0,
            target_id=None, target_name=None, target_type=None,
            direction=AttentionDirection.RIGHT,
            confidence=0.8, zone_id="zone_1",
            state=AttentionState.ATTENDING,
        )
        event = tracker.get_active_event(1)
        assert event is not None
        assert event.target_id == "unknown"
        assert event.target_type == "unknown"

    def test_unknown_direction_does_not_create_event(self):
        tracker = AttentionTracker()
        tracker.update(
            track_id=1, frame=10, timestamp=1.0,
            target_id=None, target_name=None, target_type=None,
            direction=AttentionDirection.UNKNOWN,
            confidence=0.3, zone_id="zone_1",
            state=AttentionState.UNKNOWN,
        )
        event = tracker.get_active_event(1)
        assert event is None


# ==================================================================
# TEST 7: Attention event creation
# ==================================================================
class TestAttentionEventCreation:
    """Verify structured events with all required fields."""

    def test_event_has_all_fields(self):
        tracker = AttentionTracker()
        tracker.update(
            track_id=7, frame=100, timestamp=10.0,
            target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
            direction=AttentionDirection.RIGHT,
            confidence=0.82, zone_id="zone_1",
            state=AttentionState.ATTENDING,
        )
        # Close via target change
        tracker.update(
            track_id=7, frame=200, timestamp=20.0,
            target_id="shelf_2", target_name="Snacks Shelf", target_type="shelf",
            direction=AttentionDirection.LEFT,
            confidence=0.75, zone_id="zone_1",
            state=AttentionState.ATTENDING,
        )

        events = tracker.get_events_for_track(7)
        assert len(events) >= 1

        ev = events[0]
        assert ev.tracking_id == 7
        assert ev.target_id == "shelf_1"
        assert ev.target_name == "Beverage Shelf"
        assert ev.target_type == "shelf"
        assert ev.zone_id == "zone_1"
        assert ev.attention_direction == "RIGHT"
        assert ev.status == "completed"
        assert ev.visit_number == 1

    def test_event_to_dict(self):
        event = AttentionEvent(
            tracking_id=7, zone_id="zone_1",
            target_type="shelf", target_id="shelf_1",
            target_name="Beverage Shelf",
            start_time=35.2, attention_direction="RIGHT",
            confidence=0.82, start_frame=1056,
        )
        event.close(41.8, 1254)
        d = event.to_dict()

        assert d["tracking_id"] == 7
        assert d["target_id"] == "shelf_1"
        assert d["start_time"] == 35.2
        assert d["end_time"] == 41.8
        assert abs(d["duration_seconds"] - 6.6) < 0.01
        assert d["status"] == "completed"


# ==================================================================
# TEST 8: Attention duration calculation
# ==================================================================
class TestAttentionDurationCalculation:
    """Verify start/end/duration math."""

    def test_basic_duration(self):
        event = AttentionEvent(
            tracking_id=1, zone_id="z1", target_type="shelf",
            target_id="s1", target_name="Shelf A", start_time=10.0,
            start_frame=300,
        )
        event.close(20.0, 600)
        assert event.duration_seconds == 10.0

    def test_short_duration(self):
        event = AttentionEvent(
            tracking_id=1, zone_id="z1", target_type="shelf",
            target_id="s1", target_name="Shelf A", start_time=5.5,
            start_frame=165,
        )
        event.close(6.2, 186)
        assert abs(event.duration_seconds - 0.7) < 0.01

    def test_duration_via_tracker(self):
        tracker = AttentionTracker()
        # Start attention at 35.2s
        tracker.update(
            track_id=7, frame=1056, timestamp=35.2,
            target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
            direction=AttentionDirection.RIGHT, confidence=0.82,
            zone_id="zone_1", state=AttentionState.ATTENDING,
        )
        # Extend attention at 38.0s
        tracker.update(
            track_id=7, frame=1140, timestamp=38.0,
            target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
            direction=AttentionDirection.RIGHT, confidence=0.85,
            zone_id="zone_1", state=AttentionState.ATTENDING,
        )
        # End attention at 41.8s (change target)
        tracker.update(
            track_id=7, frame=1254, timestamp=41.8,
            target_id=None, target_name=None, target_type=None,
            direction=AttentionDirection.UNKNOWN, confidence=0.0,
            zone_id="zone_1", state=AttentionState.UNKNOWN,
        )

        events = tracker.get_events_for_track(7)
        assert len(events) == 1
        assert abs(events[0].duration_seconds - 6.6) < 0.01


# ==================================================================
# TEST 9: Repeated attention events
# ==================================================================
class TestRepeatedAttentionEvents:
    """Multiple visits to same target should be preserved separately."""

    def test_two_visits_to_same_shelf(self):
        tracker = AttentionTracker()

        # Visit 1 to shelf_1
        tracker.update(1, 10, 1.0, "shelf_1", "Shelf A", "shelf",
                       AttentionDirection.RIGHT, 0.8, "z1", AttentionState.ATTENDING)
        tracker.update(1, 60, 6.0, "shelf_1", "Shelf A", "shelf",
                       AttentionDirection.RIGHT, 0.85, "z1", AttentionState.ATTENDING)
        # Break
        tracker.update(1, 70, 7.0, None, None, None,
                       AttentionDirection.UNKNOWN, 0.0, "z1", AttentionState.UNKNOWN)
        # Visit 2 to shelf_1
        tracker.update(1, 100, 10.0, "shelf_1", "Shelf A", "shelf",
                       AttentionDirection.RIGHT, 0.82, "z1", AttentionState.ATTENDING)
        tracker.update(1, 140, 14.0, "shelf_1", "Shelf A", "shelf",
                       AttentionDirection.RIGHT, 0.83, "z1", AttentionState.ATTENDING)
        # Final close
        tracker.close_remaining_events(150, 15.0)

        events = tracker.get_events_for_track(1)
        shelf_events = [e for e in events if e.target_id == "shelf_1"]

        assert len(shelf_events) == 2
        assert shelf_events[0].visit_number == 1
        assert shelf_events[1].visit_number == 2

    def test_visit_count_and_total_duration(self):
        tracker = AttentionTracker()

        # 3 visits to shelf_1
        for visit in range(3):
            start_ts = visit * 10.0
            tracker.update(1, visit * 100, start_ts, "s1", "Shelf", "shelf",
                           AttentionDirection.RIGHT, 0.8, "z1", AttentionState.ATTENDING)
            tracker.update(1, visit * 100 + 50, start_ts + 5.0, "s1", "Shelf", "shelf",
                           AttentionDirection.RIGHT, 0.8, "z1", AttentionState.ATTENDING)
            # Break
            tracker.update(1, visit * 100 + 60, start_ts + 6.0, None, None, None,
                           AttentionDirection.UNKNOWN, 0.0, "z1", AttentionState.UNKNOWN)

        events = tracker.get_events_for_target("s1")
        assert len(events) == 3

        durations = [e.duration_seconds for e in events if e.duration_seconds]
        total_duration = sum(durations)
        avg_duration = total_duration / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        assert len(durations) == 3
        assert total_duration > 0
        assert avg_duration > 0
        assert max_duration > 0


# ==================================================================
# TEST 10: Low-visibility handling
# ==================================================================
class TestLowVisibilityHandling:
    """No face/occluded/small → UNKNOWN, no fake events."""

    def test_no_face_detected_gives_no_event(self):
        """If face is never detected, no attention events should be generated."""
        tracker = AttentionTracker()

        # Only UNKNOWN updates (simulating no face detected)
        for f in range(10):
            tracker.update(
                track_id=1, frame=f, timestamp=f * 0.1,
                target_id=None, target_name=None, target_type=None,
                direction=AttentionDirection.UNKNOWN,
                confidence=0.0, zone_id="zone_1",
                state=AttentionState.UNKNOWN,
            )

        events = tracker.get_all_events()
        assert len(events) == 0

    def test_track_lost_with_no_active_event(self):
        """handle_lost_track with no active event should return empty list."""
        tracker = AttentionTracker()
        closed = tracker.handle_lost_track(1, 100, 10.0)
        assert len(closed) == 0

    def test_track_lost_closes_active_event(self):
        """handle_lost_track should close active event as track_lost."""
        tracker = AttentionTracker()
        tracker.update(1, 10, 1.0, "s1", "Shelf", "shelf",
                       AttentionDirection.RIGHT, 0.8, "z1", AttentionState.ATTENDING)
        closed = tracker.handle_lost_track(1, 50, 5.0)
        assert len(closed) == 1
        assert closed[0].status == "track_lost"
        assert closed[0].duration_seconds == 4.0

    def test_unknown_count_tracked(self):
        """Unknown observations should be counted per track."""
        tracker = AttentionTracker()
        # 5 unknown observations
        for f in range(5):
            tracker.update(1, f, f * 0.1, None, None, None,
                           AttentionDirection.UNKNOWN, 0.0, "z1",
                           AttentionState.UNKNOWN)
        # 3 valid observations
        for f in range(5, 8):
            tracker.update(1, f, f * 0.1, "s1", "Shelf", "shelf",
                           AttentionDirection.RIGHT, 0.8, "z1",
                           AttentionState.ATTENDING)

        stats = tracker.get_track_stats(1)
        assert stats["unknown_count"] == 5
        assert stats["total_observations"] == 8

    def test_no_detection_result_fields(self):
        """NO_DETECTION should not be mistaken for a valid detection."""
        assert NO_DETECTION.face_detected is False
        assert NO_DETECTION.confidence == 0.0
        assert NO_DETECTION.face_bbox == (0, 0, 0, 0)
        assert NO_DETECTION.nose_point == (0, 0)
