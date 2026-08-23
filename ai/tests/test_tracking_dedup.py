"""
Unit and Integration Tests — Person Tracking Robustness & Deduplication
========================================================================
Verifies multi-frame confirmation, occlusion-resistant tracking,
spatial-temporal trajectory stitching, and transient noise pruning.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.movement_analysis.session_manager import SessionManager, ShopperSession
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.zone_manager import ZoneManager
from ai.person_detection.detector import Detection
from ai.person_tracking.config import PersonTrackingConfig
from ai.person_tracking.tracker import PersonTracker, TrackInfo


def test_session_manager_trajectory_stitching():
    """Verify that fragmented tracks within Delta t <= 3s and Delta d <= 180px are stitched."""
    sm = SessionManager(stitching_max_time_sec=3.0, stitching_max_distance_px=180.0, min_lifetime_frames=10)

    # Shopper 1 tracked as ID 1 from frame 1 to 30 at (100, 200)
    for f in range(1, 31):
        sm.update_session(
            track_id=1,
            frame=f,
            timestamp=f / 30.0,
            confidence=0.85,
            position=(100 + f, 200),
            bbox=(90 + f, 150, 110 + f, 250),
        )

    assert len(sm._sessions) == 1
    session_1 = sm.get_session(1)
    assert session_1 is not None
    assert session_1.tracking_id == 1
    assert session_1.frames_tracked == 30
    assert session_1.last_position == (130, 200)

    # Occlusion occurs: 20 frames elapse (~0.67s). Shopper reappears at frame 51 as track ID 2 at (140, 205)
    sm.update_session(
        track_id=2,
        frame=51,
        timestamp=51 / 30.0,
        confidence=0.82,
        position=(140, 205),
        bbox=(130, 155, 150, 255),
    )

    # Should stitch into session 1 without creating a second session!
    assert len(sm._sessions) == 1
    session_stitched = sm.get_session(2)
    assert session_stitched is not None
    assert session_stitched.session_id == session_1.session_id
    assert session_stitched.tracking_id == 1
    assert 2 in session_stitched.stitched_track_ids


def test_transient_noise_pruning():
    """Verify that fleeting noise tracks (<15 frames) are flagged as transient_noise and pruned."""
    sm = SessionManager(min_lifetime_frames=15)

    # Real shopper: 40 frames
    for f in range(1, 41):
        sm.update_session(track_id=10, frame=f, timestamp=f / 30.0, confidence=0.90)

    # Fleeting noise artifact: 3 frames
    for f in range(5, 8):
        sm.update_session(track_id=99, frame=f, timestamp=f / 30.0, confidence=0.35)

    # Create real or mock zone manager for finalize
    zm = ZoneManager(Path("ai/configs/zones.json"))
    pt = PathTracker()
    zt = ZoneTracker(zm)
    eem = EntryExitMonitor(zm)

    sm.finalize_all(pt, zt, eem, min_frames=15)

    session_10 = sm.get_session(10)
    session_99 = sm.get_session(99)

    assert session_10 is not None
    assert session_10.status != "transient_noise"

    assert session_99 is not None
    assert session_99.status == "transient_noise"

    # Confirmed sessions count should be exactly 1
    confirmed = sm.get_all_sessions(include_transient=False)
    assert len(confirmed) == 1
    assert confirmed[0].tracking_id == 10
    assert sm.get_confirmed_count() == 1


def test_tracker_confirmed_unique_tracks():
    """Verify confirmed_unique_tracks filters transient short tracks."""
    from ai.person_detection.config import PersonDetectionConfig

    det_cfg = PersonDetectionConfig(
        person_model_path=Path("ai/models/yolov8n.pt"),
        confidence_threshold=0.45,
        image_size=640,
        device="cpu",
        save_frames=False,
        output_base=Path("outputs"),
        videos_dir=Path("outputs/videos"),
        frames_dir=Path("outputs/frames"),
        reports_dir=Path("outputs/reports"),
        logs_dir=Path("outputs/logs"),
    )

    track_cfg = PersonTrackingConfig(
        detection_config=det_cfg,
        track_high_threshold=0.55,
        track_low_threshold=0.15,
        new_track_threshold=0.45,
        track_buffer=90,
        match_threshold=0.70,
        minimum_consecutive_frames=3,
        min_track_frames=15,
    )

    tracker = PersonTracker(track_cfg)

    # Add a persistent track (20 frames)
    t1 = TrackInfo(1, 1, 0.033, (100, 100, 150, 200), 0.85)
    for f in range(2, 21):
        t1.update(f, f * 0.033, (100, 100, 150, 200), 0.85)
    tracker.track_history[1] = t1

    # Add a fleeting noise track (2 frames)
    t2 = TrackInfo(2, 5, 0.165, (300, 300, 320, 350), 0.40)
    t2.update(6, 0.198, (300, 300, 320, 350), 0.40)
    tracker.track_history[2] = t2

    assert tracker.total_unique_tracks == 2
    assert tracker.confirmed_unique_tracks == 1
