"""
Attention Analysis CLI Entry Point (Module 3, Phase 5)
========================================================
CLI tool for running independent attention/gaze analysis on video files
or live webcam feeds.

Usage:
    python ai/attention_analysis.py --source /path/to/video.mp4
    python ai/attention_analysis.py --source 0
    python ai/attention_analysis.py --source video.mp4 --conf 0.35 --device cpu

Outputs generated under outputs/module3/phase5/:
  - videos/   : annotated MP4 video with attention overlays
  - reports/  : attention_events.json, shopper/target summaries, attention_report.md
  - plots/    : 5 matplotlib visualizations
  - logs/     : attention_analysis.log

All attention values are estimated based on head orientation (yaw/pitch/roll),
not pixel-level eye gaze tracking.
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
from ai.attention_analysis.config import AttentionAnalysisConfig, load_attention_analysis_config
from ai.attention_analysis.head_pose_estimator import HeadPoseEstimator
from ai.attention_analysis.attention_classifier import AttentionClassifier
from ai.attention_analysis.temporal_smoother import TemporalSmoother
from ai.attention_analysis.attention_region_manager import AttentionRegionManager
from ai.attention_analysis.attention_tracker import AttentionTracker
from ai.attention_analysis.visualizer import AttentionVisualizer
from ai.attention_analysis.video_processor import AttentionVideoProcessor
# pyrefly: ignore [missing-import]
from ai.attention_analysis.report import AttentionReportGenerator
from ai.attention_analysis.plots import AttentionPlotGenerator
from ai.dwell_time_analysis.dwell_tracker import DwellTracker
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
        description="Indrani AI — Module 3 Phase 5: Attention / Gaze Analysis",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source", type=str, required=True,
        help="Path to video file or webcam index (e.g., '0' for default camera)",
    )
    parser.add_argument(
        "--zones", type=str, default="",
        help="Path to zones.json (default: from .env ZONE_CONFIG_PATH)",
    )
    parser.add_argument(
        "--attention-regions", type=str, default="",
        help="Path to attention_regions.json (default: from .env ATTENTION_REGIONS_PATH)",
    )
    parser.add_argument(
        "--conf", type=float, default=None,
        help="Person detection confidence threshold",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Inference device: 'cpu', 'cuda', or 'auto'",
    )
    parser.add_argument(
        "--output", type=str, default="",
        help="Output base directory (default: outputs/module3/phase5)",
    )
    return parser.parse_args()


def main() -> None:
    """Main CLI execution for Phase 5 Attention Analysis."""
    args = parse_args()

    # Load configuration
    try:
        config = load_attention_analysis_config()
    except Exception as exc:
        print(f"[ERROR] Failed to load configuration: {exc}", file=sys.stderr)
        sys.exit(1)

    # Set up logger
    ensure_directory(config.logs_dir)
    log_file = config.logs_dir / "attention_analysis.log"
    logger = setup_logger("attention_analysis_cli", log_file=log_file)

    logger.info("=" * 60)
    logger.info("INDRANI CONSUMER ATTENTION MAPPING SYSTEM")
    logger.info("Module 3 — Phase 5: Attention / Gaze Analysis")
    logger.info("=" * 60)
    logger.info("NOTE: All attention values are estimated based on head")
    logger.info("orientation, not pixel-level eye gaze tracking.")
    logger.info("=" * 60)

    # Resolve zone config path
    dwell_cfg = config.dwell_config
    mvmt_cfg = dwell_cfg.movement_config
    zone_config_path = Path(args.zones) if args.zones else mvmt_cfg.zone_config_path
    if not zone_config_path.is_absolute():
        zone_config_path = _PROJECT_ROOT / zone_config_path

    if not zone_config_path.exists():
        logger.error(f"Zone config file not found: {zone_config_path}")
        sys.exit(1)

    # Resolve attention regions path
    regions_path = (
        Path(args.attention_regions) if args.attention_regions
        else config.attention_regions_path
    )
    if not regions_path.is_absolute():
        regions_path = _PROJECT_ROOT / regions_path

    if not regions_path.exists():
        logger.error(f"Attention regions config not found: {regions_path}")
        sys.exit(1)

    # Initialize components
    try:
        logger.info("Loading configuration...")
        logger.info(f"  Attention confidence threshold: {config.attention_confidence_threshold}")
        logger.info(f"  Attention smoothing window: {config.attention_smoothing_window}")
        logger.info(f"  Face process interval: {config.attention_face_process_interval}")

        # Zone Manager (Phase 3)
        logger.info("Loading zone configuration...")
        zone_manager = ZoneManager(config_path=zone_config_path, logger=logger)

        # Person Detector (Phase 1)
        logger.info("Loading YOLOv8...")
        person_cfg = mvmt_cfg.tracking_config.detection_config
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
        logger.info("Loading tracking system...")
        tracker = PersonTracker(
            config=mvmt_cfg.tracking_config, logger=logger,
        )

        # Movement Analysis (Phase 3)
        path_tracker = PathTracker(
            history_length=mvmt_cfg.path_history_length, logger=logger,
        )
        zone_tracker = ZoneTracker(zone_manager=zone_manager, logger=logger)
        entry_exit_monitor = EntryExitMonitor(zone_manager=zone_manager, logger=logger)
        session_manager = SessionManager(logger=logger)

        # Dwell Tracker (Phase 4)
        dwell_tracker = DwellTracker(
            gap_tolerance=dwell_cfg.dwell_track_gap_tolerance, logger=logger,
        )

        # Head Pose Estimator (Phase 5)
        logger.info("Loading attention model...")
        head_pose_estimator = HeadPoseEstimator(
            min_detection_confidence=0.5, logger=logger,
        )

        # Attention Classifier (Phase 5)
        attention_classifier = AttentionClassifier(
            yaw_threshold=15.0, pitch_threshold=15.0,
        )

        # Temporal Smoother (Phase 5)
        temporal_smoother = TemporalSmoother(
            window_size=config.attention_smoothing_window,
        )

        # Attention Region Manager (Phase 5)
        logger.info("Loading attention regions...")
        region_manager = AttentionRegionManager(
            config_path=regions_path, logger=logger,
        )

        # Attention Tracker (Phase 5)
        attention_tracker = AttentionTracker(
            min_duration=config.attention_min_duration, logger=logger,
        )

        # Visualizer (Phase 5)
        visualizer = AttentionVisualizer(
            path_tracking_enabled=mvmt_cfg.path_tracking_enabled,
        )

    except Exception as exc:
        logger.error(f"Initialization error: {exc}", exc_info=True)
        sys.exit(1)

    # Video Processor (Phase 5)
    processor = AttentionVideoProcessor(
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
        head_pose_estimator=head_pose_estimator,
        attention_classifier=attention_classifier,
        temporal_smoother=temporal_smoother,
        region_manager=region_manager,
        attention_tracker=attention_tracker,
        visualizer=visualizer,
        logger=logger,
    )

    if processor.is_webcam:
        logger.info("Starting attention analysis...")
        processor.process_webcam()
        logger.info("Webcam processing finished.")
        return

    # Process video file
    try:
        logger.info("Starting attention analysis...")
        processing_stats = processor.process_video_file()
    except Exception as exc:
        logger.error(f"Processing error: {exc}", exc_info=True)
        sys.exit(1)

    # Report Generation
    logger.info("Generating attention events...")
    logger.info("Generating reports...")
    report_gen = AttentionReportGenerator(
        reports_dir=config.reports_dir, logger=logger,
    )

    target_summaries_for_plots = report_gen._compute_target_summaries(
        attention_tracker.get_all_events(), region_manager,
    )

    report_gen.generate(
        processing_stats=processing_stats,
        attention_tracker=attention_tracker,
        region_manager=region_manager,
        session_manager=session_manager,
    )

    # Plot Generation
    logger.info("Generating plots...")
    plot_gen = AttentionPlotGenerator(
        plots_dir=config.plots_dir, logger=logger,
    )
    plot_gen.generate_all(
        events=attention_tracker.get_all_events(),
        target_summaries=target_summaries_for_plots,
    )

    # Console Summary
    _print_console_summary(processing_stats, attention_tracker, region_manager, config)

    logger.info("Done.")


def _print_console_summary(
    stats: dict,
    attention_tracker: AttentionTracker,
    region_manager: AttentionRegionManager,
    config: AttentionAnalysisConfig,
) -> None:
    """Print clean summary table to console."""
    all_events = attention_tracker.get_all_events()
    durations = [
        e.duration_seconds for e in all_events
        if e.duration_seconds is not None and e.duration_seconds > 0
    ]
    total_attn = sum(durations) if durations else 0.0
    avg_attn = total_attn / len(durations) if durations else 0.0
    max_attn = max(durations) if durations else 0.0

    print("\n" + "=" * 65)
    print(" ATTENTION ANALYSIS SUMMARY (Module 3 — Phase 5)")
    print(" (All values are ESTIMATED from head orientation)")
    print("=" * 65)
    print(f" Source Video            : {stats.get('video_filename')}")
    print(f" Processing Speed        : {stats.get('processing_fps'):.1f} FPS")
    print(f" Total Unique Shoppers   : {stats.get('total_unique_shoppers')}")
    print(f" Total Attention Events  : {len(all_events)}")
    print(f" Total Est. Attention    : {total_attn:.1f} sec")
    print(f" Average Est. Attention  : {avg_attn:.2f} sec")
    print(f" Longest Attention Event : {max_attn:.2f} sec")
    print(f" Confidence Threshold    : {config.attention_confidence_threshold}")
    print(f" Smoothing Window        : {config.attention_smoothing_window}")
    print(f" Face Process Interval   : every {config.attention_face_process_interval} frames")

    # Per-target summary
    from collections import defaultdict
    target_stats = defaultdict(lambda: {"events": 0, "duration": 0.0, "shoppers": set()})
    for e in all_events:
        ts = target_stats[e.target_name]
        ts["events"] += 1
        if e.duration_seconds and e.duration_seconds > 0:
            ts["duration"] += e.duration_seconds
        ts["shoppers"].add(e.tracking_id)

    if target_stats:
        print("\n TARGET-WISE ATTENTION BREAKDOWN:")
        print("-" * 65)
        print(f" {'Target':<25} {'Shoppers':<10} {'Events':<8} {'Total Est. Attn':<15}")
        print("-" * 65)
        for name, ts in target_stats.items():
            print(
                f" {name:<25} {len(ts['shoppers']):<10} "
                f"{ts['events']:<8} {ts['duration']:<15.1f}"
            )
        print("-" * 65)

    print("\n OUTPUT ARTIFACTS GENERATED:")
    print(f"  - Video Report  : {stats.get('output_video')}")
    print(f"  - Reports Dir   : {config.reports_dir}")
    print(f"  - Plots Dir     : {config.plots_dir}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
