"""
Attention Report — Runner
==========================
Execution entry point for Module 3 Phase 6 attention report generation.
"""

from typing import Any
import sys
import logging
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
_AI_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AI_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.attention_report.config import ReportConfig, load_report_config
from ai.attention_report.input_validator import InputValidator
from ai.attention_report.data_loader import ReportDataLoader
from ai.attention_report.aggregator import ReportAggregator
from ai.attention_report.json_writer import JsonReportWriter
from ai.attention_report.markdown_writer import MarkdownReportWriter
from ai.attention_report.plots import ReportPlotter
from ai.logger import setup_logger


def run_phase6_report(
    config: Optional[ReportConfig] = None,
    base_dir: Optional[Any] = None,
    logger: Optional[logging.Logger] = None,
) -> int:
    """
    Execute the Phase 6 attention report generation pipeline.

    Parameters
    ----------
    config : Optional[ReportConfig]
        Report configuration. If None, loaded from environment or base_dir.
    base_dir : Optional[Any]
        Base directory containing phase3, phase4, phase5 outputs.
    logger : Optional[logging.Logger]
        Logger instance.

    Returns
    -------
    int
        0 on success, non-zero on failure.
    """
    log = logger or setup_logger("phase6_report")
    log.info("Starting Phase 6 Attention Report generation...")

    if config is None:
        config = load_report_config(base_dir=base_dir)

    # 1. Validate inputs
    validator = InputValidator(config, logger=log)
    val_result = validator.validate_all()
    if not val_result.is_valid:
        log.error("Input validation failed:")
        for err in val_result.all_errors:
            log.error(f"  {err}")
        return 1

    for warn in val_result.all_warnings:
        log.warning(f"  {warn}")

    # 2. Load data
    loader = ReportDataLoader(config, logger=log)
    data = loader.load(val_result)

    # 3. Aggregate metrics
    aggregator = ReportAggregator(data, logger=log)
    report_dict = aggregator.aggregate_all()

    # 4. Write JSON report
    json_writer = JsonReportWriter(config, logger=log)
    json_path = json_writer.write(report_dict)
    log.info(f"JSON report generated: {json_path}")

    # 5. Write Markdown report
    md_writer = MarkdownReportWriter(config, logger=log)
    md_path = md_writer.write(report_dict)
    log.info(f"Markdown report generated: {md_path}")

    # 6. Generate visualization charts
    plotter = ReportPlotter(config.plots_dir, logger=log)
    plots = plotter.generate_all(report_dict)
    log.info(f"Generated {len(plots)} charts in {config.plots_dir}")

    log.info("Phase 6 Attention Report completed successfully.")
    return 0


def main(args=None) -> int:
    """CLI entry point for running Phase 6 report."""
    return run_phase6_report()


if __name__ == "__main__":
    sys.exit(main())
