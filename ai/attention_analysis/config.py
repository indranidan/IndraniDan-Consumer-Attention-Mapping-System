"""
Attention Analysis — Configuration
======================================
Module-specific configuration dataclass for attention/gaze analysis
(Module 3, Phase 5). Reuses DwellTimeConfig from Phase 4 and adds
attention analysis settings. Reads settings from the project-root .env file.
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
from ai.dwell_time_analysis.config import DwellTimeConfig, load_dwell_time_config


@dataclass(frozen=True)
class AttentionAnalysisConfig:
    """Immutable configuration for the attention analysis pipeline."""

    # Underlying Phase 4 dwell-time configuration (includes Phase 1-3)
    dwell_config: DwellTimeConfig

    # Attention analysis settings
    attention_analysis_enabled: bool
    attention_confidence_threshold: float
    attention_smoothing_window: int
    attention_regions_path: Path
    attention_max_target_distance: int
    attention_face_process_interval: int
    attention_min_duration: float
    attention_debug: bool

    # Output directories (Phase 5)
    output_base: Path
    videos_dir: Path
    reports_dir: Path
    plots_dir: Path
    logs_dir: Path


def load_attention_analysis_config() -> AttentionAnalysisConfig:
    """
    Build an AttentionAnalysisConfig from environment variables.

    Reuses load_dwell_time_config() for the underlying Phase 4 config chain
    and loads Phase 5 attention analysis settings.

    Returns
    -------
    AttentionAnalysisConfig
        Fully constructed configuration object.
    """
    _ensure_env_loaded()

    # Load base dwell-time config from Phase 4
    dwell_config = load_dwell_time_config()

    # Attention analysis settings
    enabled_val = _optional_env("ATTENTION_ANALYSIS_ENABLED", "true").lower()
    attention_analysis_enabled = enabled_val in ("true", "1", "yes")

    attention_confidence_threshold = float(
        _optional_env("ATTENTION_CONFIDENCE_THRESHOLD", "0.60")
    )

    attention_smoothing_window = int(
        _optional_env("ATTENTION_SMOOTHING_WINDOW", "5")
    )

    regions_raw = _optional_env(
        "ATTENTION_REGIONS_PATH", "ai/configs/attention_regions.json"
    )
    attention_regions_path = Path(regions_raw)
    if not attention_regions_path.is_absolute():
        attention_regions_path = CONFIG_PROJECT_ROOT / attention_regions_path

    attention_max_target_distance = int(
        _optional_env("ATTENTION_MAX_TARGET_DISTANCE", "500")
    )

    attention_face_process_interval = int(
        _optional_env("ATTENTION_FACE_PROCESS_INTERVAL", "2")
    )

    attention_min_duration = float(
        _optional_env("ATTENTION_MIN_DURATION", "0.3")
    )

    debug_val = _optional_env("ATTENTION_DEBUG", "false").lower()
    attention_debug = debug_val in ("true", "1", "yes")

    # Phase 5 output directory hierarchy
    output_raw = _optional_env("ATTENTION_OUTPUT_PATH", "outputs/module3/phase5")
    output_base = Path(output_raw)
    if not output_base.is_absolute():
        output_base = CONFIG_PROJECT_ROOT / output_base

    videos_dir = output_base / "videos"
    reports_dir = output_base / "reports"
    plots_dir = output_base / "plots"
    logs_dir = output_base / "logs"

    return AttentionAnalysisConfig(
        dwell_config=dwell_config,
        attention_analysis_enabled=attention_analysis_enabled,
        attention_confidence_threshold=attention_confidence_threshold,
        attention_smoothing_window=attention_smoothing_window,
        attention_regions_path=attention_regions_path,
        attention_max_target_distance=attention_max_target_distance,
        attention_face_process_interval=attention_face_process_interval,
        attention_min_duration=attention_min_duration,
        attention_debug=attention_debug,
        output_base=output_base,
        videos_dir=videos_dir,
        reports_dir=reports_dir,
        plots_dir=plots_dir,
        logs_dir=logs_dir,
    )
