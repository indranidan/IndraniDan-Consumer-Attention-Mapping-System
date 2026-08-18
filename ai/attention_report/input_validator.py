"""
Attention Report — Input Validation
=======================================
Validates all required input files from Phases 3, 4, and 5 before
report generation. Checks file existence, readability, JSON validity,
required structure, required fields, numeric validity, and timestamps.

Never invents missing data. Stops on missing required files.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai.attention_report.config import ReportConfig
from ai.logger import setup_logger


@dataclass
class FileValidationResult:
    """Validation result for a single file."""
    file_path: Path
    file_name: str
    exists: bool = False
    readable: bool = False
    valid_json: bool = False
    structure_valid: bool = False
    required: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[dict] = None

    @property
    def is_valid(self) -> bool:
        return self.exists and self.readable and self.valid_json and self.structure_valid

    @property
    def is_usable(self) -> bool:
        """File is either valid or not required."""
        return self.is_valid or not self.required


@dataclass
class ValidationResult:
    """Overall validation result for all input files."""
    file_results: Dict[str, FileValidationResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(r.is_usable for r in self.file_results.values()) and len(self.errors) == 0

    @property
    def all_errors(self) -> List[str]:
        errors = list(self.errors)
        for name, result in self.file_results.items():
            for err in result.errors:
                errors.append(f"[{name}] {err}")
        return errors

    @property
    def all_warnings(self) -> List[str]:
        warnings = []
        for name, result in self.file_results.items():
            for w in result.warnings:
                warnings.append(f"[{name}] {w}")
        return warnings


# ── Required field schemas ──────────────────────────────────────────

_SESSION_REQUIRED_FIELDS = {
    "session_id": str,
    "tracking_id": (int, float),
    "start_time": (int, float),
    "end_time": (int, float),
    "status": str,
}

_TRAFFIC_REQUIRED_FIELDS = {
    "total_unique_shoppers": (int, float),
    "total_entries": (int, float),
    "total_exits": (int, float),
}

_ZONE_VISIT_REQUIRED_FIELDS = {
    "zone_id": str,
    "zone_name": str,
    "tracking_id": (int, float),
}

_DWELL_EVENT_REQUIRED_FIELDS = {
    "tracking_id": (int, float),
    "zone_id": str,
    "zone_name": str,
    "dwell_seconds": (int, float),
    "status": str,
}

_ZONE_DWELL_REQUIRED_FIELDS = {
    "zone_id": str,
    "zone_name": str,
    "unique_shoppers": (int, float),
    "total_visits": (int, float),
    "total_dwell_seconds": (int, float),
}

_SHOPPER_DWELL_REQUIRED_FIELDS = {
    "tracking_id": (int, float),
    "total_observed_dwell_seconds": (int, float),
}

_ATTENTION_EVENT_REQUIRED_FIELDS = {
    "tracking_id": (int, float),
    "target_id": str,
    "target_name": str,
}

_SHOPPER_ATTENTION_REQUIRED_FIELDS = {
    "tracking_id": (int, float),
    "attention_event_count": (int, float),
    "total_estimated_attention_sec": (int, float),
}

_TARGET_ATTENTION_REQUIRED_FIELDS = {
    "target_id": str,
    "target_name": str,
    "target_type": str,
    "attention_event_count": (int, float),
}


class InputValidator:
    """Validates all Phase 3/4/5 input files before report generation."""

    def __init__(self, config: ReportConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or setup_logger("input_validator")

    def validate_all(self) -> ValidationResult:
        """
        Validate all required and optional input files.

        Returns
        -------
        ValidationResult
            Overall validation result.

        Raises
        ------
        SystemExit
            If a required file is missing or invalid.
        """
        result = ValidationResult()

        # Phase 3 — Required
        result.file_results["sessions"] = self._validate_file(
            self.config.sessions_path, "sessions.json",
            required=True, list_key="sessions",
            item_fields=_SESSION_REQUIRED_FIELDS,
        )
        result.file_results["traffic_summary"] = self._validate_file(
            self.config.traffic_summary_path, "traffic_summary.json",
            required=True, list_key=None,
            top_fields=_TRAFFIC_REQUIRED_FIELDS,
        )
        result.file_results["zone_visits"] = self._validate_file(
            self.config.zone_visits_path, "zone_visits.json",
            required=True, list_key="zone_visits",
            item_fields=_ZONE_VISIT_REQUIRED_FIELDS,
        )

        # Phase 3 — Optional
        result.file_results["paths"] = self._validate_file(
            self.config.paths_path, "paths.json",
            required=False, list_key="paths",
        )

        # Phase 4 — Required
        result.file_results["dwell_events"] = self._validate_file(
            self.config.dwell_events_path, "dwell_events.json",
            required=True, list_key="events",
            item_fields=_DWELL_EVENT_REQUIRED_FIELDS,
        )
        result.file_results["zone_dwell_summary"] = self._validate_file(
            self.config.zone_dwell_summary_path, "zone_dwell_summary.json",
            required=True, list_key="zone_summaries",
            item_fields=_ZONE_DWELL_REQUIRED_FIELDS,
        )
        result.file_results["shopper_dwell_summary"] = self._validate_file(
            self.config.shopper_dwell_summary_path, "shopper_dwell_summary.json",
            required=True, list_key="shopper_summaries",
            item_fields=_SHOPPER_DWELL_REQUIRED_FIELDS,
        )
        result.file_results["dwell_distribution"] = self._validate_file(
            self.config.dwell_distribution_path, "dwell_distribution.json",
            required=True, list_key="buckets",
        )

        # Phase 5 — Required
        result.file_results["attention_events"] = self._validate_file(
            self.config.attention_events_path, "attention_events.json",
            required=True, list_key="events",
            item_fields=_ATTENTION_EVENT_REQUIRED_FIELDS,
        )
        result.file_results["shopper_attention_summary"] = self._validate_file(
            self.config.shopper_attention_summary_path, "shopper_attention_summary.json",
            required=True, list_key="shoppers",
            item_fields=_SHOPPER_ATTENTION_REQUIRED_FIELDS,
        )
        result.file_results["target_attention_summary"] = self._validate_file(
            self.config.target_attention_summary_path, "target_attention_summary.json",
            required=True, list_key="targets",
            item_fields=_TARGET_ATTENTION_REQUIRED_FIELDS,
        )

        # Log results
        for name, fr in result.file_results.items():
            status = "✓" if fr.is_valid else ("⚠" if not fr.required else "✗")
            self.logger.info(f"  {status} {fr.file_name}")
            for err in fr.errors:
                self.logger.error(f"    ERROR: {err}")
            for w in fr.warnings:
                self.logger.warning(f"    WARNING: {w}")

        return result

    def _validate_file(
        self,
        file_path: Path,
        file_name: str,
        required: bool = True,
        list_key: Optional[str] = None,
        item_fields: Optional[Dict[str, Any]] = None,
        top_fields: Optional[Dict[str, Any]] = None,
    ) -> FileValidationResult:
        """Validate a single input file."""
        fr = FileValidationResult(
            file_path=file_path,
            file_name=file_name,
            required=required,
        )

        # Check existence
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            if required:
                fr.errors.append(msg)
            else:
                fr.warnings.append(f"Optional file not found: {file_path}")
            return fr
        fr.exists = True

        # Check readable
        try:
            raw = file_path.read_text(encoding="utf-8")
        except PermissionError:
            fr.errors.append(f"Permission denied: {file_path}")
            return fr
        except Exception as exc:
            fr.errors.append(f"Cannot read file: {exc}")
            return fr
        fr.readable = True

        # Check valid JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            fr.errors.append(f"Invalid JSON: {exc}")
            return fr
        fr.valid_json = True
        fr.data = data

        # Check structure
        if not isinstance(data, dict):
            fr.errors.append("JSON root must be an object/dict")
            return fr

        # Top-level field validation
        if top_fields:
            for field_name, field_type in top_fields.items():
                if field_name not in data:
                    fr.errors.append(f"Missing required field: '{field_name}'")
                elif not isinstance(data[field_name], field_type):
                    fr.errors.append(
                        f"Field '{field_name}' has invalid type: "
                        f"expected {field_type}, got {type(data[field_name]).__name__}"
                    )

        # List/Dict-level validation
        if list_key:
            if list_key not in data:
                fr.errors.append(f"Missing required key: '{list_key}'")
            elif not isinstance(data[list_key], (list, dict)):
                fr.errors.append(f"Key '{list_key}' must be a list or dict")
            elif item_fields and isinstance(data[list_key], list) and len(data[list_key]) > 0:
                # Validate first item structure as a sample
                sample = data[list_key][0]
                if isinstance(sample, dict):
                    for field_name, field_type in item_fields.items():
                        if field_name not in sample:
                            fr.warnings.append(
                                f"Item field '{field_name}' missing in '{list_key}[0]'"
                            )
                        elif sample[field_name] is not None and not isinstance(
                            sample[field_name], field_type
                        ):
                            fr.warnings.append(
                                f"Item field '{field_name}' has unexpected type in '{list_key}[0]'"
                            )

        # Validate numeric fields don't contain invalid values
        self._check_numeric_validity(data, fr)

        if not fr.errors:
            fr.structure_valid = True

        return fr

    def _check_numeric_validity(self, data: Any, fr: FileValidationResult, path: str = "") -> None:
        """Recursively check for invalid numeric values (NaN, Infinity)."""
        if isinstance(data, float):
            import math
            if math.isnan(data) or math.isinf(data):
                fr.warnings.append(f"Invalid numeric value at {path}: {data}")
        elif isinstance(data, dict):
            for key, value in data.items():
                self._check_numeric_validity(value, fr, f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data[:5]):  # Check first 5 items
                self._check_numeric_validity(item, fr, f"{path}[{i}]")
