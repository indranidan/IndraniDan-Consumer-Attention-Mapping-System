"""
Attention Report — Configuration
===================================
Module-specific configuration for the Phase 6 report generator.
Reads paths and settings from the project-root .env file.
Does NOT modify any existing configuration or module.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AI_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import _ensure_env_loaded, _optional_env, _PROJECT_ROOT as CONFIG_ROOT


def _resolve_path(raw: str) -> Path:
    """Resolve a path relative to project root if not absolute."""
    p = Path(raw)
    if not p.is_absolute():
        p = CONFIG_ROOT / p
    return p


@dataclass(frozen=True)
class ReportConfig:
    """Immutable configuration for the Phase 6 report generator."""

    # Input paths (previous phase outputs)
    phase3_output_path: Path
    phase4_output_path: Path
    phase5_output_path: Path

    # Output paths
    phase6_output_path: Path
    reports_dir: Path
    plots_dir: Path
    logs_dir: Path

    # Report settings
    report_version: str

    # Metadata from existing config (read-only, for inclusion in reports)
    device: str
    person_model_path: str
    attention_confidence_threshold: float
    attention_smoothing_window: int
    attention_regions_path: Path
    zone_config_path: Path

    # Project paths
    ai_dir: Path
    project_root: Path

    # Phase 3 input files
    @property
    def sessions_path(self) -> Path:
        return self.phase3_output_path / "sessions.json"

    @property
    def paths_path(self) -> Path:
        return self.phase3_output_path / "paths.json"

    @property
    def zone_visits_path(self) -> Path:
        return self.phase3_output_path / "zone_visits.json"

    @property
    def traffic_summary_path(self) -> Path:
        return self.phase3_output_path / "traffic_summary.json"

    # Phase 4 input files
    @property
    def dwell_events_path(self) -> Path:
        return self.phase4_output_path / "dwell_events.json"

    @property
    def zone_dwell_summary_path(self) -> Path:
        return self.phase4_output_path / "zone_dwell_summary.json"

    @property
    def shopper_dwell_summary_path(self) -> Path:
        return self.phase4_output_path / "shopper_dwell_summary.json"

    @property
    def dwell_distribution_path(self) -> Path:
        return self.phase4_output_path / "dwell_distribution.json"

    # Phase 5 input files
    @property
    def attention_events_path(self) -> Path:
        return self.phase5_output_path / "attention_events.json"

    @property
    def shopper_attention_summary_path(self) -> Path:
        return self.phase5_output_path / "shopper_attention_summary.json"

    @property
    def target_attention_summary_path(self) -> Path:
        return self.phase5_output_path / "target_attention_summary.json"


def load_report_config() -> ReportConfig:
    """
    Build a ReportConfig from environment variables.

    Returns
    -------
    ReportConfig
        Fully validated, immutable configuration object.

    Raises
    ------
    RuntimeError
        If .env is missing or required variables are not set.
    """
    _ensure_env_loaded()

    phase3 = _resolve_path(_optional_env("PHASE3_OUTPUT_PATH", "outputs/module3/phase3/reports"))
    phase4 = _resolve_path(_optional_env("PHASE4_OUTPUT_PATH", "outputs/module3/phase4/reports"))
    phase5 = _resolve_path(_optional_env("PHASE5_OUTPUT_PATH", "outputs/module3/phase5/reports"))
    phase6 = _resolve_path(_optional_env("PHASE6_OUTPUT_PATH", "outputs/module3/phase6"))

    report_version = _optional_env("REPORT_VERSION", "1.0")

    device = _optional_env("DEVICE", "cpu")
    person_model = _optional_env("PERSON_MODEL_PATH", "ai/yolo26n.pt")
    confidence_threshold = float(_optional_env("ATTENTION_CONFIDENCE_THRESHOLD", "0.60"))
    smoothing_window = int(_optional_env("ATTENTION_SMOOTHING_WINDOW", "5"))

    regions_raw = _optional_env("ATTENTION_REGIONS_PATH", "ai/configs/attention_regions.json")
    regions_path = _resolve_path(regions_raw)

    zone_raw = _optional_env("ZONE_CONFIG_PATH", "ai/configs/zones.json")
    zone_path = _resolve_path(zone_raw)

    return ReportConfig(
        phase3_output_path=phase3,
        phase4_output_path=phase4,
        phase5_output_path=phase5,
        phase6_output_path=phase6,
        reports_dir=phase6 / "reports",
        plots_dir=phase6 / "plots",
        logs_dir=phase6 / "logs",
        report_version=report_version,
        device=device,
        person_model_path=person_model,
        attention_confidence_threshold=confidence_threshold,
        attention_smoothing_window=smoothing_window,
        attention_regions_path=regions_path,
        zone_config_path=zone_path,
        ai_dir=_AI_DIR,
        project_root=_PROJECT_ROOT,
    )
