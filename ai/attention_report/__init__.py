"""
Attention Report — Package
==============================
Module 3 Phase 6: Standalone attention reporting and analytics
presentation layer. Reads structured outputs from Phases 3, 4,
and 5 to generate comprehensive JSON, Markdown, and chart reports.

This module does NOT perform any video processing, detection,
tracking, or gaze estimation. It is ONLY a reporting layer.
"""

from ai.attention_report.config import ReportConfig, load_report_config
from ai.attention_report.input_validator import InputValidator
from ai.attention_report.data_loader import ReportDataLoader
from ai.attention_report.aggregator import ReportAggregator

__all__ = [
    "ReportConfig",
    "load_report_config",
    "InputValidator",
    "ReportDataLoader",
    "ReportAggregator",
]
