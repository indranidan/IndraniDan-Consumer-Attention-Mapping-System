"""
Dwell-Time Analysis — Configuration
=======================================
Module-specific configuration dataclass for dwell-time analytics (Module 3, Phase 4).
Reuses MovementAnalysisConfig from Phase 3 and adds dwell-time settings.
Reads settings from the project-root .env file.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Ensure project root is in sys.path
_AI_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AI_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import _ensure_env_loaded, _optional_env, _PROJECT_ROOT as CONFIG_PROJECT_ROOT
from ai.movement_analysis.config import MovementAnalysisConfig, load_movement_analysis_config


@dataclass(frozen=True)
class DwellTimeConfig:
    """Immutable configuration for the dwell-time analytics pipeline."""

    # Underlying Phase 3 movement analysis configuration
    movement_config: MovementAnalysisConfig

    # Dwell-time settings
    dwell_time_enabled: bool
    dwell_track_gap_tolerance: int
    dwell_distribution_buckets: List[int]

    # Output directories (Phase 4)
    output_base: Path
    videos_dir: Path
    reports_dir: Path
    plots_dir: Path
    logs_dir: Path


def _parse_buckets(raw: str) -> List[int]:
    """Parse comma-separated bucket boundaries from env string."""
    parts = [s.strip() for s in raw.split(",") if s.strip()]
    buckets = []
    for part in parts:
        try:
            val = int(part)
            if val > 0:
                buckets.append(val)
        except ValueError:
            continue
    return sorted(buckets) if buckets else [10, 30, 60, 120]


def load_dwell_time_config() -> DwellTimeConfig:
    """
    Build a DwellTimeConfig from environment variables.

    Reuses load_movement_analysis_config() for the underlying Phase 3 config chain
    and loads Phase 4 dwell-time settings.

    Returns
    -------
    DwellTimeConfig
        Fully constructed configuration object.
    """
    _ensure_env_loaded()

    # Load base movement analysis config from Phase 3
    movement_config = load_movement_analysis_config()

    # Dwell-time settings
    dwell_enabled_val = _optional_env("DWELL_TIME_ENABLED", "true").lower()
    dwell_time_enabled = dwell_enabled_val in ("true", "1", "yes")

    dwell_track_gap_tolerance = int(
        _optional_env("DWELL_TRACK_GAP_TOLERANCE", "15")
    )

    buckets_raw = _optional_env("DWELL_DISTRIBUTION_BUCKETS", "10,30,60,120")
    dwell_distribution_buckets = _parse_buckets(buckets_raw)

    # Phase 4 output directory hierarchy
    output_raw = _optional_env("DWELL_OUTPUT_PATH", "outputs/module3/phase4")
    output_base = Path(output_raw)
    if not output_base.is_absolute():
        output_base = CONFIG_PROJECT_ROOT / output_base

    videos_dir = output_base / "videos"
    reports_dir = output_base / "reports"
    plots_dir = output_base / "plots"
    logs_dir = output_base / "logs"

    return DwellTimeConfig(
        movement_config=movement_config,
        dwell_time_enabled=dwell_time_enabled,
        dwell_track_gap_tolerance=dwell_track_gap_tolerance,
        dwell_distribution_buckets=dwell_distribution_buckets,
        output_base=output_base,
        videos_dir=videos_dir,
        reports_dir=reports_dir,
        plots_dir=plots_dir,
        logs_dir=logs_dir,
    )
