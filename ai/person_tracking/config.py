"""
Person Tracking — Configuration
================================
Module-specific configuration dataclass for person tracking (Module 3, Phase 2).
Reuses PersonDetectionConfig from Phase 1 and adds ByteTrack parameters.
Reads settings from the project-root .env file.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is in sys.path
_AI_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AI_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import _ensure_env_loaded, _optional_env, _PROJECT_ROOT as CONFIG_PROJECT_ROOT
from ai.person_detection.config import PersonDetectionConfig, load_person_detection_config


@dataclass(frozen=True)
class PersonTrackingConfig:
    """Immutable configuration for the person tracking pipeline."""

    # Underlying Phase 1 person detection config
    detection_config: PersonDetectionConfig

    # ByteTrack Tracker settings
    track_high_threshold: float
    track_low_threshold: float
    new_track_threshold: float
    track_buffer: int
    match_threshold: float

    # Visualizer settings
    trajectory_enabled: bool
    trajectory_length: int

    # Output control
    output_base: Path

    # Derived paths
    videos_dir: Path
    frames_dir: Path
    reports_dir: Path
    logs_dir: Path


def load_person_tracking_config() -> PersonTrackingConfig:
    """
    Build a PersonTrackingConfig from environment variables.

    Reuses load_person_detection_config() for YOLO detection parameters
    and loads ByteTrack tracking settings.

    Returns
    -------
    PersonTrackingConfig
        Fully constructed configuration object.
    """
    _ensure_env_loaded()

    # Load base detection config from Phase 1
    detection_config = load_person_detection_config()

    # ByteTrack settings with sensible retail video defaults
    track_high_thresh = float(
        _optional_env("TRACKER_TRACK_HIGH_THRESHOLD", "0.60")
    )
    track_low_thresh = float(
        _optional_env("TRACKER_TRACK_LOW_THRESHOLD", "0.10")
    )
    new_track_thresh = float(
        _optional_env("TRACKER_NEW_TRACK_THRESHOLD", "0.25")
    )
    track_buffer = int(_optional_env("TRACKER_TRACK_BUFFER", "30"))
    match_thresh = float(_optional_env("TRACKER_MATCH_THRESHOLD", "0.80"))

    # Trajectory settings
    traj_enabled_val = _optional_env("TRACK_TRAJECTORY_ENABLED", "true").lower()
    trajectory_enabled = traj_enabled_val in ("true", "1", "yes")
    trajectory_length = int(_optional_env("TRACK_TRAJECTORY_LENGTH", "30"))

    # Phase 2 Output directory hierarchy
    output_base = CONFIG_PROJECT_ROOT / "outputs" / "module3" / "phase2"
    videos_dir = output_base / "videos"
    frames_dir = output_base / "frames"
    reports_dir = output_base / "reports"
    logs_dir = output_base / "logs"

    return PersonTrackingConfig(
        detection_config=detection_config,
        track_high_threshold=track_high_thresh,
        track_low_threshold=track_low_thresh,
        new_track_threshold=new_track_thresh,
        track_buffer=track_buffer,
        match_threshold=match_thresh,
        trajectory_enabled=trajectory_enabled,
        trajectory_length=trajectory_length,
        output_base=output_base,
        videos_dir=videos_dir,
        frames_dir=frames_dir,
        reports_dir=reports_dir,
        logs_dir=logs_dir,
    )
