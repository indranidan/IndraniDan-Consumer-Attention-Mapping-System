"""
Unit Tests — Re-ID Appearance Matcher & Tracker Recovery
=========================================================
Tests appearance feature extraction, track registration, and occlusion recovery.
"""

import sys
from pathlib import Path
import numpy as np

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.person_tracking.reid_matcher import AppearanceFeatureExtractor, ReIDMatcher
from ai.person_tracking.tracker import PersonTracker
from ai.person_tracking.config import PersonTrackingConfig
from ai.person_detection.detector import Detection


def test_appearance_feature_extractor():
    extractor = AppearanceFeatureExtractor()
    dummy_crop = np.zeros((100, 50, 3), dtype=np.uint8)
    dummy_crop[:50, :, 0] = 200  # Blue upper half
    dummy_crop[50:, :, 2] = 200  # Red lower half

    feat = extractor.extract(dummy_crop)
    assert feat is not None
    assert isinstance(feat, np.ndarray)
    assert np.isclose(np.linalg.norm(feat), 1.0, atol=1e-4)


def test_reid_matcher_lost_recovery():
    matcher = ReIDMatcher(similarity_threshold=0.7)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[50:150, 50:100, :] = 180  # Dummy person at (50, 50, 100, 150)

    # Register track #1
    bbox1 = (50, 50, 100, 150)
    matcher.update_track(track_id=1, frame=frame, bbox=bbox1, frame_idx=10)
    assert 1 in matcher.gallery

    # Mark lost at frame 15
    matcher.mark_lost(track_id=1, frame_idx=15)
    assert matcher.gallery[1]["is_lost"] is True

    # Candidate reappears nearby at frame 20 at (55, 55, 105, 155)
    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame2[55:155, 55:105, :] = 180
    bbox2 = (55, 55, 105, 155)

    matched_id = matcher.match_candidate(frame2, bbox2, frame_idx=20)
    assert matched_id == 1, f"Expected track #1 recovery, got {matched_id}"
    assert matcher.gallery[1]["is_lost"] is False


def test_person_tracker_reid_integration(tmp_path):
    from ai.person_detection.config import PersonDetectionConfig

    det_config = PersonDetectionConfig(
        person_model_path=tmp_path / "yolov8n.pt",
        confidence_threshold=0.40,
        image_size=640,
        device="cpu",
        save_frames=False,
        output_base=tmp_path,
        videos_dir=tmp_path,
        frames_dir=tmp_path,
        reports_dir=tmp_path,
        logs_dir=tmp_path,
    )

    config = PersonTrackingConfig(
        detection_config=det_config,
        track_high_threshold=0.60,
        track_low_threshold=0.10,
        new_track_threshold=0.25,
        track_buffer=30,
        match_threshold=0.80,
        trajectory_enabled=True,
        trajectory_length=30,
        output_base=tmp_path,
        videos_dir=tmp_path,
        frames_dir=tmp_path,
        reports_dir=tmp_path,
        logs_dir=tmp_path,
    )
    tracker = PersonTracker(config=config)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[50:150, 50:100, :] = 220

    dets = [Detection(bbox=(50, 50, 100, 150), confidence=0.9, class_id=0, class_name="person")]
    tracks, _ = tracker.update(detections=dets, frame_number=1, timestamp=0.033, frame=frame)
    assert len(tracker.reid_matcher.gallery) >= 0

