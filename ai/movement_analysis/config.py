"""
Movement Analysis — Configuration
====================================
Module-specific configuration dataclass for movement analysis (Module 3, Phase 3).
Reuses PersonTrackingConfig from Phase 2 and adds zone/path/entry-exit settings.
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
from ai.person_tracking.config import PersonTrackingConfig, load_person_tracking_config


@dataclass(frozen=True)
class MovementAnalysisConfig:
    """Immutable configuration for the movement analysis pipeline."""

    # Underlying Phase 2 tracking configuration (includes Phase 1 detection)
    tracking_config: PersonTrackingConfig

    # Path tracking settings
    path_tracking_enabled: bool
    path_history_length: int

    # Zone tracking settings
    zone_tracking_enabled: bool
    zone_config_path: Path

    # Entry/exit monitoring settings
    entry_exit_enabled: bool

    # Traffic analytics settings
    traffic_analytics_enabled: bool

    # Output directories (Phase 3)
    output_base: Path
    videos_dir: Path
    reports_dir: Path
    logs_dir: Path


def load_movement_analysis_config() -> MovementAnalysisConfig:
    """
    Build a MovementAnalysisConfig from environment variables.

    Reuses load_person_tracking_config() for detection and tracking parameters
    and loads Phase 3 movement analysis settings.

    Returns
    -------
    MovementAnalysisConfig
        Fully constructed configuration object.
    """
    _ensure_env_loaded()

    # Load base tracking config from Phase 2
    tracking_config = load_person_tracking_config()

    # Path tracking settings
    path_enabled_val = _optional_env("PATH_TRACKING_ENABLED", "true").lower()
    path_tracking_enabled = path_enabled_val in ("true", "1", "yes")
    path_history_length = int(_optional_env("PATH_HISTORY_LENGTH", "100"))

    # Zone tracking settings
    zone_enabled_val = _optional_env("ZONE_TRACKING_ENABLED", "true").lower()
    zone_tracking_enabled = zone_enabled_val in ("true", "1", "yes")

    zone_config_raw = _optional_env("ZONE_CONFIG_PATH", "ai/configs/zones.json")
    zone_config_path = Path(zone_config_raw)
    if not zone_config_path.is_absolute():
        zone_config_path = CONFIG_PROJECT_ROOT / zone_config_path

    # Entry/exit monitoring settings
    entry_exit_val = _optional_env("ENTRY_EXIT_ENABLED", "true").lower()
    entry_exit_enabled = entry_exit_val in ("true", "1", "yes")

    # Traffic analytics settings
    traffic_val = _optional_env("TRAFFIC_ANALYTICS_ENABLED", "true").lower()
    traffic_analytics_enabled = traffic_val in ("true", "1", "yes")

    # Phase 3 output directory hierarchy
    output_raw = _optional_env("MOVEMENT_OUTPUT_PATH", None) or _optional_env("PHASE3_OUTPUT_PATH", None)
    if output_raw:
        p = Path(output_raw)
        if not p.is_absolute():
            p = CONFIG_PROJECT_ROOT / p
        output_base = p.parent if p.name == "reports" else p
    else:
        output_base = CONFIG_PROJECT_ROOT / "outputs" / "module3" / "phase3"
    videos_dir = output_base / "videos"
    reports_dir = output_base / "reports"
    logs_dir = output_base / "logs"

    return MovementAnalysisConfig(
        tracking_config=tracking_config,
        path_tracking_enabled=path_tracking_enabled,
        path_history_length=path_history_length,
        zone_tracking_enabled=zone_tracking_enabled,
        zone_config_path=zone_config_path,
        entry_exit_enabled=entry_exit_enabled,
        traffic_analytics_enabled=traffic_analytics_enabled,
        output_base=output_base,
        videos_dir=videos_dir,
        reports_dir=reports_dir,
        logs_dir=logs_dir,
    )
