"""
Module 3 Phase 2 — Person Tracking Tests
==========================================
Unit and integration tests for ByteTrack multi-person tracking:
- Config loading & validation
- ByteTrack initialization & state reset
- Single-person tracking & ID persistence
- Multi-person tracking with distinct IDs
- New person entering scene
- Person disappearing from scene
- Trajectory path collection
- Invalid detection handling
- Video source validation & error handling
- Tracking report generation

Run:
    python -m pytest ai/tests/test_person_tracking.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.person_detection.detector import Detection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def tracking_config(tmp_path):
    """Create a PersonTrackingConfig with test parameters."""
    from ai.person_detection.config import PersonDetectionConfig
    from ai.person_tracking.config import PersonTrackingConfig

    det_output = tmp_path / "outputs" / "module3" / "phase1"
    track_output = tmp_path / "outputs" / "module3" / "phase2"

    det_config = PersonDetectionConfig(
        person_model_path=tmp_path / "yolov8n.pt",
        confidence_threshold=0.40,
        image_size=640,
        device="cpu",
        save_frames=False,
        output_base=det_output,
        videos_dir=det_output / "videos",
        frames_dir=det_output / "frames",
        reports_dir=det_output / "reports",
        logs_dir=det_output / "logs",
    )

    return PersonTrackingConfig(
        detection_config=det_config,
        track_high_threshold=0.60,
        track_low_threshold=0.10,
        new_track_threshold=0.25,
        track_buffer=30,
        match_threshold=0.80,
        trajectory_enabled=True,
        trajectory_length=30,
        output_base=track_output,
        videos_dir=track_output / "videos",
        frames_dir=track_output / "frames",
        reports_dir=track_output / "reports",
        logs_dir=track_output / "logs",
    )


# ---------------------------------------------------------------------------
# Test 1: Configuration Loading
# ---------------------------------------------------------------------------
class TestTrackingConfiguration:
    """Test PersonTrackingConfig loading and immutability."""

    def test_load_tracking_config(self):
        """Config should load successfully from environment."""
        from ai.person_tracking.config import load_person_tracking_config

        config = load_person_tracking_config()
        assert config.track_high_threshold > 0
        assert config.track_buffer > 0
        assert config.match_threshold > 0
        assert config.output_base is not None

    def test_config_immutable(self, tracking_config):
        """PersonTrackingConfig should be frozen."""
        with pytest.raises(AttributeError):
            tracking_config.track_buffer = 50


# ---------------------------------------------------------------------------
# Test 2: ByteTrack Initialization
# ---------------------------------------------------------------------------
class TestByteTrackInitialization:
    """Test PersonTracker initialization and reset."""

    def test_tracker_initializes(self, tracking_config):
        """PersonTracker should initialize ByteTrack without error."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)
        assert tracker.byte_tracker is not None
        assert tracker.total_unique_tracks == 0
        assert tracker.max_simultaneous_tracks == 0

    def test_tracker_reset(self, tracking_config):
        """Reset should clear history and counters."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)
        dets = [
            Detection(bbox=(100, 100, 200, 300), confidence=0.85, class_id=0, class_name="person")
        ]
        # Frame 1: Tentative track initialization
        tracker.update(dets, frame_number=1, timestamp=0.033)
        # Frame 2: Confirmed track ID
        tracker.update(dets, frame_number=2, timestamp=0.066)
        assert tracker.total_unique_tracks > 0

        tracker.reset()
        assert tracker.total_unique_tracks == 0
        assert tracker.max_simultaneous_tracks == 0


# ---------------------------------------------------------------------------
# Test 3: Single-Person Tracking & ID Persistence
# ---------------------------------------------------------------------------
class TestSinglePersonTracking:
    """Test persistent tracking ID for a single person across frames."""

    def test_single_person_persistent_id(self, tracking_config):
        """A single person moving slightly across frames should retain the same tracking ID."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)

        # Frame 1: Person at (100, 100, 200, 300) - Tentative init
        dets1 = [Detection(bbox=(100, 100, 200, 300), confidence=0.90, class_id=0, class_name="person")]
        tracker.update(dets1, frame_number=1, timestamp=0.033)

        # Frame 2: Person moved slightly to (105, 102, 205, 302) - Track confirmed
        dets2 = [Detection(bbox=(105, 102, 205, 302), confidence=0.89, class_id=0, class_name="person")]
        tracks2, _ = tracker.update(dets2, frame_number=2, timestamp=0.066)

        # Frame 3: Person moved slightly to (110, 105, 210, 305) - Track maintained
        dets3 = [Detection(bbox=(110, 105, 210, 305), confidence=0.91, class_id=0, class_name="person")]
        tracks3, _ = tracker.update(dets3, frame_number=3, timestamp=0.099)

        assert len(tracks2) == 1
        assert len(tracks3) == 1

        id2 = tracks2[0].track_id
        id3 = tracks3[0].track_id

        assert id2 == id3, f"Tracking ID changed across frames: {id2} -> {id3}"



# ---------------------------------------------------------------------------
# Test 4: Multi-Person Tracking
# ---------------------------------------------------------------------------
class TestMultiPersonTracking:
    """Test tracking multiple people simultaneously."""

    def test_multiple_people_distinct_ids(self, tracking_config):
        """Multiple persons appearing together should receive distinct tracking IDs."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)

        dets = [
            Detection(bbox=(100, 100, 200, 300), confidence=0.90, class_id=0, class_name="person"),
            Detection(bbox=(400, 150, 500, 350), confidence=0.85, class_id=0, class_name="person"),
            Detection(bbox=(700, 200, 800, 400), confidence=0.92, class_id=0, class_name="person"),
        ]

        # Update over 2 frames to confirm assigned IDs
        tracker.update(dets, frame_number=1, timestamp=0.033)
        tracks, _ = tracker.update(dets, frame_number=2, timestamp=0.066)

        assert len(tracks) == 3
        ids = {t.track_id for t in tracks}
        assert len(ids) == 3, f"Expected 3 distinct IDs, got {ids}"


# ---------------------------------------------------------------------------
# Test 5: New Person Entering Scene
# ---------------------------------------------------------------------------
class TestNewPersonEntering:
    """Test handling of a new person entering the scene."""

    def test_new_person_gets_new_id(self, tracking_config):
        """When a new person enters, they should receive a new unique tracking ID."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)

        # Frames 1-2: Person A only
        dets_a = [Detection(bbox=(100, 100, 200, 300), confidence=0.90, class_id=0, class_name="person")]
        tracker.update(dets_a, frame_number=1, timestamp=0.033)
        tracks_f2, _ = tracker.update(dets_a, frame_number=2, timestamp=0.066)

        person_a_id = tracks_f2[0].track_id

        # Frames 3-4: Person A + Person B enters at (500, 100, 600, 300)
        dets_ab = [
            Detection(bbox=(102, 101, 202, 301), confidence=0.90, class_id=0, class_name="person"),
            Detection(bbox=(500, 100, 600, 300), confidence=0.88, class_id=0, class_name="person"),
        ]
        tracker.update(dets_ab, frame_number=3, timestamp=0.099)
        tracks_f4, _ = tracker.update(dets_ab, frame_number=4, timestamp=0.132)

        assert len(tracks_f4) == 2
        f4_ids = {t.track_id for t in tracks_f4}
        assert person_a_id in f4_ids
        assert len(f4_ids) == 2


# ---------------------------------------------------------------------------
# Test 6: Person Disappearing from Scene
# ---------------------------------------------------------------------------
class TestPersonDisappearing:
    """Test behavior when a person disappears from the video."""

    def test_person_disappearing_handling(self, tracking_config):
        """When a person leaves, tracker active count should decrease."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)

        dets_two = [
            Detection(bbox=(100, 100, 200, 300), confidence=0.90, class_id=0, class_name="person"),
            Detection(bbox=(500, 100, 600, 300), confidence=0.88, class_id=0, class_name="person"),
        ]
        tracker.update(dets_two, frame_number=1, timestamp=0.033)
        tracks_f2, _ = tracker.update(dets_two, frame_number=2, timestamp=0.066)
        assert len(tracks_f2) == 2

        # Frame 3: Only Person 1 remains (Person 2 disappeared)
        dets_one = [
            Detection(bbox=(105, 102, 205, 302), confidence=0.90, class_id=0, class_name="person"),
        ]
        tracks_f3, _ = tracker.update(dets_one, frame_number=3, timestamp=0.099)
        assert len(tracks_f3) == 1


# ---------------------------------------------------------------------------
# Test 7: Trajectory History
# ---------------------------------------------------------------------------
class TestTrajectoryCollection:
    """Test trajectory path deque recording."""

    def test_trajectory_length_bounded(self, tracking_config):
        """Trajectory history should record centers up to trajectory_length maxlen."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)

        for i in range(50):
            x = 100 + i * 2
            dets = [Detection(bbox=(x, 100, x + 100, 300), confidence=0.90, class_id=0, class_name="person")]
            tracker.update(dets, frame_number=i + 1, timestamp=(i + 1) * 0.033)

        assert tracker.total_unique_tracks == 1
        track_info = tracker.track_history[1]
        assert len(track_info.trajectory) == tracking_config.trajectory_length


# ---------------------------------------------------------------------------
# Test 8: Invalid Detection & Video Handling
# ---------------------------------------------------------------------------
class TestInvalidInputs:
    """Test empty detections and invalid video source handling."""

    def test_empty_detections_handling(self, tracking_config):
        """Updating tracker with empty detections list should return empty tracks."""
        from ai.person_tracking.tracker import PersonTracker

        tracker = PersonTracker(tracking_config)
        tracks, t_ms = tracker.update([], frame_number=1, timestamp=0.033)

        assert tracks == []
        assert t_ms >= 0

    def test_invalid_video_path_raises_error(self, tracking_config):
        """TrackingVideoProcessor should raise FileNotFoundError for missing video file."""
        from ai.person_tracking.video_processor import TrackingVideoProcessor

        processor = TrackingVideoProcessor(
            source="/invalid/non_existent_video.mp4",
            config=tracking_config,
            detector=None,
            tracker=None,
            visualizer=None,
        )

        with pytest.raises(FileNotFoundError):
            processor.open()

    def test_invalid_webcam_index_raises_error(self, tracking_config):
        """TrackingVideoProcessor should raise RuntimeError for invalid webcam index."""
        from ai.person_tracking.video_processor import TrackingVideoProcessor

        processor = TrackingVideoProcessor(
            source="999",
            config=tracking_config,
            detector=None,
            tracker=None,
            visualizer=None,
        )

        with pytest.raises(RuntimeError):
            processor.open()


# ---------------------------------------------------------------------------
# Test 9: Report Generation
# ---------------------------------------------------------------------------
class TestTrackingReportGeneration:
    """Test creation of JSON, Markdown, and tracks.json reports."""

    def test_reports_generation(self, tmp_path, tracking_config):
        """TrackingReportGenerator should create all three report artifacts."""
        from ai.person_tracking.report import TrackingReportGenerator
        from ai.person_tracking.tracker import TrackInfo

        reporter = TrackingReportGenerator(tmp_path)

        session_stats = {
            "video_filename": "test_video.mp4",
            "video_path": "/path/to/test_video.mp4",
            "video_duration_sec": 10.0,
            "video_resolution": "1280x720",
            "video_fps": 30.0,
            "total_frames_processed": 300,
            "total_unique_tracking_ids": 2,
            "max_simultaneous_tracked_people": 2,
            "average_active_tracks": 1.5,
            "total_person_detections": 450,
            "average_yolo_inference_time_ms": 25.0,
            "average_bytetrack_time_ms": 2.5,
            "average_tracking_confidence": 0.88,
            "total_pipeline_time_sec": 12.0,
            "processing_fps": 25.0,
            "device": "cpu",
            "model": "/path/to/model.pt",
            "tracker": "ByteTrack",
            "track_high_threshold": 0.60,
            "track_low_threshold": 0.10,
            "new_track_threshold": 0.25,
            "track_buffer": 30,
            "match_threshold": 0.80,
            "output_video": str(tmp_path / "output.mp4"),
        }

        t1 = TrackInfo(1, 1, 0.033, (100, 100, 200, 300), 0.90)
        t2 = TrackInfo(2, 10, 0.33, (400, 150, 500, 350), 0.85)
        track_history = {1: t1, 2: t2}

        frame_records = [
            {
                "frame": 1,
                "timestamp": 0.033,
                "active_tracks_count": 1,
                "tracks": [{"track_id": 1, "bbox": [100, 100, 200, 300], "confidence": 0.90, "center": [150, 200]}],
            }
        ]

        json_path, md_path, tracks_path = reporter.generate(session_stats, track_history, frame_records)

        assert json_path.exists()
        assert md_path.exists()
        assert tracks_path.exists()

        # Check JSON contents
        import json

        with open(json_path) as f:
            j_data = json.load(f)
        assert j_data["total_unique_tracking_ids"] == 2
        assert len(j_data["tracks_summary"]) == 2

        # Check Markdown contents
        md_text = md_path.read_text()
        assert "Multi-Person Tracking Report" in md_text
        assert "test_video.mp4" in md_text

        # Check tracks.json contents
        with open(tracks_path) as f:
            t_data = json.load(f)
        assert len(t_data["frames"]) == 1
