"""
Dwell-Time Analytics CLI Entry Point (Module 3, Phase 4)
=========================================================
CLI tool for running independent dwell-time analytics on video files or live webcam feeds.

Usage:
    python ai/dwell_time.py --source /path/to/video.mp4
    python ai/dwell_time.py --source 0 --zones ai/configs/zones.json
    python ai/dwell_time.py --source video.mp4 --conf 0.35 --device cpu

Outputs generated under outputs/module3/phase4/:
  - videos/        : annotated MP4 video with live dwell overlays
  - reports/       : dwell_events.json, zone_dwell_summary.json, shopper_dwell_summary.json, dwell_distribution.json, dwell_time_report.md
  - plots/         : avg_dwell_by_zone.png, total_dwell_by_zone.png, visit_count_by_zone.png, dwell_distribution.png
  - logs/          : dwell_time.log
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
_AI_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AI_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.logger import setup_logger
from ai.dwell_time_analysis.config import DwellTimeConfig, load_dwell_time_config
from ai.dwell_time_analysis.dwell_tracker import DwellTracker
from ai.dwell_time_analysis.dwell_aggregator import DwellAggregator
from ai.dwell_time_analysis.report import DwellReportGenerator
from ai.dwell_time_analysis.plots import DwellPlotGenerator
from ai.dwell_time_analysis.visualizer import DwellVisualizer
from ai.dwell_time_analysis.video_processor import DwellVideoProcessor
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.person_detection.detector import PersonDetector
from ai.person_tracking.tracker import PersonTracker
from ai.utils import ensure_directory


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Indrani AI — Module 3 Phase 4: Dwell-Time Analytics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to video file or webcam index (e.g., '0' for default camera)",
    )
    parser.add_argument(
        "--zones",
        type=str,
        default="",
        help="Path to zones.json configuration file (default: from .env ZONE_CONFIG_PATH)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="Person detection confidence threshold (default: from .env PERSON_CONFIDENCE_THRESHOLD)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Inference device: 'cpu', 'cuda', or 'auto' (default: from .env DEVICE)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output base directory (default: outputs/module3/phase4)",
    )

    return parser.parse_args()


def main() -> None:
    """Main CLI execution for Phase 4 Dwell-Time Analytics."""
    args = parse_args()

    # Load configuration
    try:
        config = load_dwell_time_config()
    except Exception as exc:
        print(f"[ERROR] Failed to load configuration: {exc}", file=sys.stderr)
        sys.exit(1)

    # Set up logger
    ensure_directory(config.logs_dir)
    log_file = config.logs_dir / "dwell_time.log"
    logger = setup_logger("dwell_time_cli", log_file=log_file)

    logger.info("=" * 60)
    logger.info("INDRANI CONSUMER ATTENTION MAPPING SYSTEM")
    logger.info("Module 3 — Phase 4: Dwell-Time Analytics")
    logger.info("=" * 60)

    # Resolve zones config path
    zone_config_path = Path(args.zones) if args.zones else config.movement_config.zone_config_path
    if not zone_config_path.is_absolute():
        zone_config_path = _PROJECT_ROOT / zone_config_path

    if not zone_config_path.exists():
        logger.error(f"Zone config file not found: {zone_config_path}")
        sys.exit(1)

    # Initialize components
    try:
        logger.info("Initializing AI components...")

        # Zone Manager
        zone_manager = ZoneManager(config_path=zone_config_path, logger=logger)

        # Person Detector (Phase 1)
        person_cfg = config.movement_config.tracking_config.detection_config
        if args.conf is not None or args.device is not None:
            from dataclasses import replace
            kwargs = {}
            if args.conf is not None:
                kwargs["confidence_threshold"] = args.conf
            if args.device is not None:
                kwargs["device"] = args.device
            person_cfg = replace(person_cfg, **kwargs)

        detector = PersonDetector(config=person_cfg, logger=logger)

        # ByteTrack Tracker (Phase 2)
        tracker = PersonTracker(
            config=config.movement_config.tracking_config,
            logger=logger,
        )

        # Movement Analysis Trackers (Phase 3)
        path_tracker = PathTracker(
            history_length=config.movement_config.path_history_length,
            logger=logger,
        )
        zone_tracker = ZoneTracker(zone_manager=zone_manager, logger=logger)
        entry_exit_monitor = EntryExitMonitor(zone_manager=zone_manager, logger=logger)
        session_manager = SessionManager(logger=logger)

        # Dwell Tracker & Visualizer (Phase 4)
        dwell_tracker = DwellTracker(
            gap_tolerance=config.dwell_track_gap_tolerance,
            logger=logger,
        )
        visualizer = DwellVisualizer(
            path_tracking_enabled=config.movement_config.path_tracking_enabled,
        )

    except Exception as exc:
        logger.error(f"Initialization error: {exc}", exc_info=True)
        sys.exit(1)

    # Video Processor (Phase 4)
    processor = DwellVideoProcessor(
        source=args.source,
        config=config,
        detector=detector,
        tracker=tracker,
        zone_manager=zone_manager,
        path_tracker=path_tracker,
        zone_tracker=zone_tracker,
        entry_exit_monitor=entry_exit_monitor,
        session_manager=session_manager,
        dwell_tracker=dwell_tracker,
        visualizer=visualizer,
        logger=logger,
    )

    if processor.is_webcam:
        processor.process_webcam()
        logger.info("Webcam processing finished.")
        return

    # Process video file
    try:
        processing_stats = processor.process_video_file()
    except Exception as exc:
        logger.error(f"Processing error: {exc}", exc_info=True)
        sys.exit(1)

    # Dwell Aggregation (Phase 4.7, 4.8, 4.9)
    logger.info("Performing statistical aggregations...")
    aggregator = DwellAggregator(logger=logger)
    zone_summaries = aggregator.aggregate_zones(dwell_tracker, zone_manager)
    shopper_summaries = aggregator.aggregate_shoppers(dwell_tracker, session_manager)
    distribution = aggregator.compute_distribution(dwell_tracker, config.dwell_distribution_buckets)

    # Plot Generation (Phase 4.14)
    plot_gen = DwellPlotGenerator(plots_dir=config.plots_dir, logger=logger)
    plot_paths = plot_gen.generate_all(zone_summaries, distribution)

    # Report Generation (Phase 4.12, 4.13)
    report_gen = DwellReportGenerator(reports_dir=config.reports_dir, logger=logger)
    report_gen.generate(
        processing_stats=processing_stats,
        dwell_tracker=dwell_tracker,
        zone_summaries=zone_summaries,
        shopper_summaries=shopper_summaries,
        distribution=distribution,
        session_manager=session_manager,
    )

    # Print Console Summary
    _print_console_summary(processing_stats, zone_summaries, shopper_summaries, distribution, dwell_tracker, config)


def _print_console_summary(
    stats: dict,
    zone_summaries: list,
    shopper_summaries: list,
    distribution,
    dwell_tracker: DwellTracker,
    config: DwellTimeConfig,
) -> None:
    """Print clean summary table to console."""
    all_events = dwell_tracker.get_all_events()
    all_dwell = [e.dwell_seconds for e in all_events if e.dwell_seconds is not None and e.dwell_seconds >= 0]
    total_dwell = sum(all_dwell) if all_dwell else 0.0
    avg_dwell = total_dwell / len(all_dwell) if all_dwell else 0.0

    print("\n" + "=" * 65)
    print(" DWELL-TIME ANALYTICS SUMMARY (Module 3 — Phase 4)")
    print("=" * 65)
    print(f" Source Video           : {stats.get('video_filename')}")
    print(f" Processing Speed       : {stats.get('processing_fps'):.1f} FPS")
    print(f" Total Unique Shoppers  : {stats.get('total_unique_shoppers')}")
    print(f" Total Zone Visits      : {len(all_events)}")
    print(f" Total Dwell Time       : {total_dwell:.1f} sec")
    print(f" Average Dwell Time     : {avg_dwell:.2f} sec")
    print(f" Completed Visits       : {dwell_tracker.total_completed_events}")
    print(f" Track-Lost Visits      : {dwell_tracker.total_track_lost_events}")

    print("\n ZONE-WISE DWELL BREAKDOWN:")
    print("-" * 65)
    print(f" {'Zone ID':<10} {'Zone Name':<20} {'Shoppers':<10} {'Visits':<8} {'Total Dwell':<12} {'Avg Dwell':<10}")
    print("-" * 65)
    for zs in zone_summaries:
        print(
            f" {zs.zone_id:<10} {zs.zone_name:<20} {zs.unique_shoppers:<10} "
            f"{zs.total_visits:<8} {zs.total_dwell_seconds:<12.1f} {zs.average_dwell_seconds:<10.1f}"
        )
    print("-" * 65)

    print("\n DWELL-TIME DISTRIBUTION BUCKETS:")
    print("-" * 40)
    for bucket in distribution.buckets:
        print(f"  {bucket.label:<15} : {bucket.visit_count} visit(s)")
    print("-" * 40)

    print("\n OUTPUT ARTIFACTS GENERATED:")
    print(f"  - Video Report  : {stats.get('output_video')}")
    print(f"  - Reports Dir   : {config.reports_dir}")
    print(f"  - Plots Dir     : {config.plots_dir}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
