#!/usr/bin/env python3
"""
Module 3 — Phase 6: Attention Report Generator
==================================================
Standalone CLI script that generates comprehensive attention reports
from the structured outputs of Phases 3, 4, and 5.

Usage:
    python ai/generate_attention_report.py

This script does NOT:
- Process video
- Load AI models
- Require backend/frontend
- Modify any database

It operates exclusively on structured JSON data.
"""

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.attention_report.config import load_report_config
from ai.attention_report.input_validator import InputValidator
from ai.attention_report.data_loader import ReportDataLoader
from ai.attention_report.aggregator import ReportAggregator
from ai.attention_report.plots import ReportPlotter
from ai.attention_report.json_writer import JsonReportWriter
from ai.attention_report.markdown_writer import MarkdownReportWriter
from ai.logger import setup_logger
from ai.utils import ensure_directory, print_banner


def main() -> None:
    """Main entry point for Phase 6 report generation."""
    start_time = time.perf_counter()

    print_banner("Module 3 — Phase 6: Attention Report Generator")

    # ── Step 1: Load Configuration ──────────────────────────────
    logger = setup_logger("attention_report_generator")
    logger.info("Loading report configuration...")

    try:
        config = load_report_config()
    except Exception as exc:
        logger.error(f"Failed to load configuration: {exc}")
        sys.exit(1)

    # Create output directories
    ensure_directory(config.reports_dir)
    ensure_directory(config.plots_dir)
    ensure_directory(config.logs_dir)

    # Setup file logging
    log_file = config.logs_dir / "report_generation.log"
    file_logger = setup_logger(
        "attention_report_generator",
        log_file=log_file,
    )

    file_logger.info(f"Phase 3 input: {config.phase3_output_path}")
    file_logger.info(f"Phase 4 input: {config.phase4_output_path}")
    file_logger.info(f"Phase 5 input: {config.phase5_output_path}")
    file_logger.info(f"Phase 6 output: {config.phase6_output_path}")
    file_logger.info(f"Report version: {config.report_version}")

    # ── Step 2: Validate Input Data ─────────────────────────────
    file_logger.info("")
    file_logger.info("Validating input data...")
    validator = InputValidator(config, logger=file_logger)
    validation_result = validator.validate_all()

    if not validation_result.is_valid:
        file_logger.error("")
        file_logger.error("Input validation FAILED. Cannot generate report.")
        for err in validation_result.all_errors:
            file_logger.error(f"  {err}")
        sys.exit(1)

    warnings = validation_result.all_warnings
    if warnings:
        file_logger.warning(f"  {len(warnings)} validation warning(s)")
        for w in warnings:
            file_logger.warning(f"  {w}")

    file_logger.info("Input validation passed.")

    # ── Step 3: Load Validated Data ─────────────────────────────
    file_logger.info("")
    file_logger.info("Loading Phase 3 data...")
    file_logger.info("Loading Phase 4 data...")
    file_logger.info("Loading Phase 5 data...")

    loader = ReportDataLoader(config, logger=file_logger)
    data = loader.load(validation_result)

    # ── Step 4: Aggregate Analytics ─────────────────────────────
    file_logger.info("")
    aggregator = ReportAggregator(data, logger=file_logger)
    report = aggregator.aggregate_all()

    # Attach raw data for plotting
    report["_dwell_distribution"] = data.dwell_distribution
    report["_attention_events_raw"] = data.attention_events

    # ── Step 5: Generate Charts ─────────────────────────────────
    file_logger.info("")
    file_logger.info("Generating charts...")
    plotter = ReportPlotter(config.plots_dir, logger=file_logger)
    generated_plots = plotter.generate_all(report)
    file_logger.info(f"  Generated {len(generated_plots)} chart(s)")

    # ── Step 6: Generate JSON Report ────────────────────────────
    file_logger.info("")
    file_logger.info("Generating JSON report...")
    json_writer = JsonReportWriter(config, logger=file_logger)
    json_path = json_writer.write(report)

    # ── Step 7: Generate Markdown Report ────────────────────────
    file_logger.info("Generating Markdown report...")
    md_writer = MarkdownReportWriter(config, logger=file_logger)
    md_path = md_writer.write(report)

    # ── Step 8: Completion Summary ──────────────────────────────
    elapsed = time.perf_counter() - start_time

    file_logger.info("")
    file_logger.info("=" * 60)
    file_logger.info("Report generation completed.")
    file_logger.info("=" * 60)
    file_logger.info("")
    file_logger.info(f"  JSON Report  : {json_path}")
    file_logger.info(f"  Markdown     : {md_path}")
    file_logger.info(f"  Charts       : {config.plots_dir} ({len(generated_plots)} files)")
    file_logger.info(f"  Log          : {log_file}")
    file_logger.info(f"  Time Elapsed : {elapsed:.2f}s")
    file_logger.info("")

    # Summary stats
    summary = report.get("summary", {})
    file_logger.info(f"  Shoppers     : {summary.get('total_unique_shoppers', 0)}")
    file_logger.info(f"  Sessions     : {summary.get('total_sessions', 0)}")
    file_logger.info(f"  Zone Visits  : {summary.get('total_zone_visits', 0)}")
    file_logger.info(f"  Attn Events  : {summary.get('total_attention_events', 0)}")
    file_logger.info(f"  Attn Targets : {summary.get('number_of_attention_targets', 0)}")


if __name__ == "__main__":
    main()
