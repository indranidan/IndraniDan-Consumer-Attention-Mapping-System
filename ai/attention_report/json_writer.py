"""
Attention Report — JSON Writer
==================================
Generates the structured JSON attention report.
Ensures valid JSON with no NaN or Infinity values.
Uses null where a value cannot be calculated.
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ai.attention_report.config import ReportConfig
from ai.logger import setup_logger
from ai.utils import ensure_directory


def _sanitize_value(val: Any) -> Any:
    """Replace NaN/Infinity with None for JSON safety."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
    elif isinstance(val, dict):
        return {k: _sanitize_value(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_sanitize_value(v) for v in val]
    return val


class JsonReportWriter:
    """Generates the Phase 6 JSON report."""

    def __init__(self, config: ReportConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.reports_dir = ensure_directory(config.reports_dir)
        self.logger = logger or setup_logger("json_writer")

    def write(self, report: Dict[str, Any]) -> Path:
        """
        Write the full attention report as JSON.

        Parameters
        ----------
        report : dict
            Aggregated report data from ReportAggregator.

        Returns
        -------
        Path
            Path to the generated JSON report file.
        """
        metadata = {
            "report_generation_timestamp": datetime.now().isoformat(),
            "report_version": self.config.report_version,
            "device": self.config.device,
            "model": self.config.person_model_path,
            "tracker": "ByteTrack",
            "attention_confidence_threshold": self.config.attention_confidence_threshold,
            "attention_smoothing_window": self.config.attention_smoothing_window,
        }

        limitations = [
            "Attention is estimated based on head orientation, not exact eye gaze.",
            "Head pose is used as a proxy for gaze direction.",
            "Camera resolution and angle affect attention estimation accuracy.",
            "Occlusion affects face and head-pose estimation reliability.",
            "Track loss affects session and dwell-time calculations.",
            "Product-level attention is only reported when supported by the data.",
            "Attention does not imply purchase.",
            "Attention does not imply purchase intent.",
            "Dwell time does not automatically mean attention.",
            "Estimated attention is not necessarily exact eye gaze.",
        ]

        output = _sanitize_value({
            "report_version": self.config.report_version,
            "metadata": metadata,
            "summary": report.get("summary", {}),
            "shoppers": report.get("shoppers", []),
            "zones": report.get("zones", []),
            "targets": report.get("targets", []),
            "attention_direction": report.get("attention_direction", {}),
            "confidence": report.get("confidence", {}),
            "dwell_vs_attention": report.get("dwell_vs_attention", {}),
            "repeated_attention": report.get("repeated_attention", {}),
            "rankings": report.get("rankings", {}),
            "time_series": report.get("time_series", {}),
            "data_quality": report.get("data_quality", {}),
            "limitations": limitations,
        })

        path = self.reports_dir / "attention_report.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"JSON report generated: {path}")
        return path
