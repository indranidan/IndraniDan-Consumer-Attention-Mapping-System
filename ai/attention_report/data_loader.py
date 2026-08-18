"""
Attention Report — Data Loader
==================================
Loads and holds all validated JSON data from Phases 3, 4, and 5.
Provides type-safe access to all input datasets.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.attention_report.config import ReportConfig
from ai.attention_report.input_validator import InputValidator, ValidationResult
from ai.logger import setup_logger


@dataclass
class ReportData:
    """Container for all loaded Phase 3/4/5 data."""

    # Phase 3
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    traffic_summary: Dict[str, Any] = field(default_factory=dict)
    zone_visits: List[Dict[str, Any]] = field(default_factory=list)
    paths: Optional[Any] = None  # Optional (dict or list)

    # Phase 4
    dwell_events: List[Dict[str, Any]] = field(default_factory=list)
    zone_dwell_summary: List[Dict[str, Any]] = field(default_factory=list)
    shopper_dwell_summary: List[Dict[str, Any]] = field(default_factory=list)
    dwell_distribution: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 5
    attention_events: List[Dict[str, Any]] = field(default_factory=list)
    shopper_attention_summary: List[Dict[str, Any]] = field(default_factory=list)
    target_attention_summary: List[Dict[str, Any]] = field(default_factory=list)

    # Validation info
    validation_result: Optional[ValidationResult] = None


class ReportDataLoader:
    """Loads all validated input data for report generation."""

    def __init__(self, config: ReportConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or setup_logger("report_data_loader")

    def load(self, validation_result: ValidationResult) -> ReportData:
        """
        Load all validated data from Phase 3/4/5 output files.

        Parameters
        ----------
        validation_result : ValidationResult
            Pre-validated file results containing loaded data.

        Returns
        -------
        ReportData
            Container with all loaded datasets.
        """
        data = ReportData(validation_result=validation_result)

        # Phase 3
        data.sessions = self._extract_list(
            validation_result, "sessions", "sessions"
        )
        data.traffic_summary = self._extract_dict(
            validation_result, "traffic_summary"
        )
        data.zone_visits = self._extract_list(
            validation_result, "zone_visits", "zone_visits"
        )
        paths_result = validation_result.file_results.get("paths")
        if paths_result and paths_result.is_valid and paths_result.data:
            data.paths = paths_result.data.get("paths")
        else:
            data.paths = None

        # Phase 4
        data.dwell_events = self._extract_list(
            validation_result, "dwell_events", "events"
        )
        data.zone_dwell_summary = self._extract_list(
            validation_result, "zone_dwell_summary", "zone_summaries"
        )
        data.shopper_dwell_summary = self._extract_list(
            validation_result, "shopper_dwell_summary", "shopper_summaries"
        )
        data.dwell_distribution = self._extract_list(
            validation_result, "dwell_distribution", "buckets"
        )

        # Phase 5
        data.attention_events = self._extract_list(
            validation_result, "attention_events", "events"
        )
        data.shopper_attention_summary = self._extract_list(
            validation_result, "shopper_attention_summary", "shoppers"
        )
        data.target_attention_summary = self._extract_list(
            validation_result, "target_attention_summary", "targets"
        )

        self.logger.info(f"  Loaded {len(data.sessions)} sessions")
        self.logger.info(f"  Loaded {len(data.zone_visits)} zone visits")
        self.logger.info(f"  Loaded {len(data.dwell_events)} dwell events")
        self.logger.info(f"  Loaded {len(data.zone_dwell_summary)} zone dwell summaries")
        self.logger.info(f"  Loaded {len(data.shopper_dwell_summary)} shopper dwell summaries")
        self.logger.info(f"  Loaded {len(data.attention_events)} attention events")
        self.logger.info(f"  Loaded {len(data.shopper_attention_summary)} shopper attention summaries")
        self.logger.info(f"  Loaded {len(data.target_attention_summary)} target attention summaries")

        return data

    def _extract_list(
        self,
        vr: ValidationResult,
        result_key: str,
        data_key: str,
    ) -> List[Dict[str, Any]]:
        """Extract a list from a validated file result."""
        fr = vr.file_results.get(result_key)
        if fr and fr.is_valid and fr.data:
            items = fr.data.get(data_key, [])
            return items if isinstance(items, list) else []
        return []

    def _extract_dict(
        self,
        vr: ValidationResult,
        result_key: str,
    ) -> Dict[str, Any]:
        """Extract the full dict from a validated file result."""
        fr = vr.file_results.get(result_key)
        if fr and fr.is_valid and fr.data:
            return fr.data
        return {}
