"""
Module 3 — Phase 3: Movement Analysis Pipeline (CLI Entry Point)
==================================================================
Independent pipeline for shopper movement intelligence:
path tracking, zone detection, entry/exit monitoring, session generation,
and traffic statistics.

Usage:
    python ai/movement_tracking.py --source /path/to/video.mp4
    python ai/movement_tracking.py --source 0
    python ai/movement_tracking.py --source /path/to/video.mp4 --zones ai/configs/zones.json

Pipeline:
    Video/Webcam -> OpenCV -> YOLOv8 -> ByteTrack -> Path Tracking ->
    Zone Detection -> Entry/Exit -> Sessions -> Traffic Stats -> Reports
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Module 3 Phase 3 — Movement Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai/movement_tracking.py --source /path/to/video.mp4
  python ai/movement_tracking.py --source 0
  python ai/movement_tracking.py --source /path/to/video.mp4 --zones ai/configs/zones.json
  python ai/movement_tracking.py --source /path/to/video.mp4 --confidence 0.50
        """,
    )
    parser.add_argument(
        "--source", required=True,
        help="Path to video file or webcam index (e.g., 0)",
    )
    parser.add_argument(
        "--zones", type=str, default=None,
        help="Override ZONE_CONFIG_PATH: path to zones.json",
    )
    parser.add_argument(
        "--confidence", type=float, default=None,
        help="Override PERSON_CONFIDENCE_THRESHOLD (0.0-1.0)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Override output base directory",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for the movement analysis pipeline."""
    args = parse_args()

    # ── Imports after sys.path setup ──────────────────────────
    from ai.logger import setup_logger
    from ai.movement_analysis.config import (
        MovementAnalysisConfig,
        load_movement_analysis_config,
    )
    from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
    from ai.movement_analysis.movement_visualizer import MovementVisualizer
    from ai.movement_analysis.path_tracker import PathTracker
    from ai.movement_analysis.report import MovementReportGenerator
    from ai.movement_analysis.session_manager import SessionManager
    from ai.movement_analysis.video_processor import MovementVideoProcessor
    from ai.movement_analysis.zone_manager import ZoneManager
    from ai.movement_analysis.zone_tracker import ZoneTracker
    from ai.person_detection.config import PersonDetectionConfig
    from ai.person_detection.detector import PersonDetector
    from ai.person_tracking.config import PersonTrackingConfig
    from ai.person_tracking.tracker import PersonTracker
    from ai.utils import ensure_directory, print_banner

    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — Movement Analysis (Module 3, Phase 3)")

    # ── Load configuration ────────────────────────────────────
    try:
        config = load_movement_analysis_config()
    except Exception as exc:
        print(f"\n❌ Configuration error: {exc}\n")
        return 1

    # ── Apply CLI overrides ───────────────────────────────────
    if args.zones or args.confidence is not None or args.output_dir:
        tc = config.tracking_config
        dc = tc.detection_config

        # Zone config path override
        zone_config_path = config.zone_config_path
        if args.zones:
            zone_config_path = Path(args.zones)
            if not zone_config_path.is_absolute():
                zone_config_path = _PROJECT_ROOT / zone_config_path

        # Confidence override
        conf = args.confidence if args.confidence is not None else dc.confidence_threshold
        if not 0.0 <= conf <= 1.0:
            print(f"\n❌ Invalid confidence: {conf}. Must be 0.0-1.0.\n")
            return 1

        # Output dir override
        output_base = config.output_base
        if args.output_dir:
            output_base = Path(args.output_dir)
            if not output_base.is_absolute():
                output_base = _PROJECT_ROOT / output_base

        new_dc = PersonDetectionConfig(
            person_model_path=dc.person_model_path,
            confidence_threshold=conf,
            image_size=dc.image_size,
            device=dc.device,
            save_frames=dc.save_frames,
            output_base=dc.output_base,
            videos_dir=dc.videos_dir,
            frames_dir=dc.frames_dir,
            reports_dir=dc.reports_dir,
            logs_dir=dc.logs_dir,
        )

        new_tc = PersonTrackingConfig(
            detection_config=new_dc,
            track_high_threshold=tc.track_high_threshold,
            track_low_threshold=tc.track_low_threshold,
            new_track_threshold=tc.new_track_threshold,
            track_buffer=tc.track_buffer,
            match_threshold=tc.match_threshold,
            trajectory_enabled=tc.trajectory_enabled,
            trajectory_length=tc.trajectory_length,
            output_base=tc.output_base,
            videos_dir=tc.videos_dir,
            frames_dir=tc.frames_dir,
            reports_dir=tc.reports_dir,
            logs_dir=tc.logs_dir,
        )

        config = MovementAnalysisConfig(
            tracking_config=new_tc,
            path_tracking_enabled=config.path_tracking_enabled,
            path_history_length=config.path_history_length,
            zone_tracking_enabled=config.zone_tracking_enabled,
            zone_config_path=zone_config_path,
            entry_exit_enabled=config.entry_exit_enabled,
            traffic_analytics_enabled=config.traffic_analytics_enabled,
            output_base=output_base,
            videos_dir=output_base / "videos",
            reports_dir=output_base / "reports",
            logs_dir=output_base / "logs",
        )

    # ── Setup logging ─────────────────────────────────────────
    log_dir = ensure_directory(config.logs_dir)
    log_file = log_dir / "movement_tracking.log"
    logger = setup_logger("movement_tracking", log_file=log_file)

    logger.info("Loading configuration...")
    logger.info(f"  Model                : {config.tracking_config.detection_config.person_model_path}")
    logger.info(f"  Confidence           : {config.tracking_config.detection_config.confidence_threshold}")
    logger.info(f"  Tracker              : ByteTrack")
    logger.info(f"  Path tracking        : {config.path_tracking_enabled}")
    logger.info(f"  Path history length  : {config.path_history_length}")
    logger.info(f"  Zone tracking        : {config.zone_tracking_enabled}")
    logger.info(f"  Zone config          : {config.zone_config_path}")
    logger.info(f"  Entry/exit monitoring: {config.entry_exit_enabled}")
    logger.info(f"  Traffic analytics    : {config.traffic_analytics_enabled}")
    logger.info(f"  Output directory     : {config.output_base}")

    # ── Determine source type ─────────────────────────────────
    is_webcam = False
    try:
        int(args.source)
        is_webcam = True
    except (ValueError, TypeError):
        pass

    logger.info(f"  Source                : {'Webcam ' + args.source if is_webcam else args.source}")

    # ── Load zone configuration ───────────────────────────────
    try:
        logger.info("Loading zone configuration...")
        zone_manager = ZoneManager(config.zone_config_path, logger=logger)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        print(f"\n❌ Zone config error: {exc}\n")
        return 1
    except ValueError as exc:
        logger.error(str(exc))
        print(f"\n❌ Zone config validation error: {exc}\n")
        return 1

    # ── Initialize detector (Phase 1) ─────────────────────────
    try:
        logger.info("Loading YOLOv8 person detection model...")
        detector = PersonDetector(config.tracking_config.detection_config, logger=logger)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error(str(exc))
        print(f"\n❌ Model error: {exc}\n")
        return 1

    # ── Initialize tracker (Phase 2) ──────────────────────────
    logger.info("Initializing ByteTrack...")
    tracker = PersonTracker(config=config.tracking_config, logger=logger)

    # ── Initialize Phase 3 analytics ──────────────────────────
    path_tracker = PathTracker(
        history_length=config.path_history_length, logger=logger
    )
    zone_tracker = ZoneTracker(zone_manager=zone_manager, logger=logger)
    entry_exit_monitor = EntryExitMonitor(zone_manager=zone_manager, logger=logger)
    session_manager = SessionManager(logger=logger)
    visualizer = MovementVisualizer(
        path_tracking_enabled=config.path_tracking_enabled
    )

    # ── Initialize video processor ────────────────────────────
    processor = MovementVideoProcessor(
        source=args.source,
        config=config,
        detector=detector,
        tracker=tracker,
        zone_manager=zone_manager,
        path_tracker=path_tracker,
        zone_tracker=zone_tracker,
        entry_exit_monitor=entry_exit_monitor,
        session_manager=session_manager,
        visualizer=visualizer,
        logger=logger,
    )

    # ── Execute ───────────────────────────────────────────────
    try:
        if is_webcam:
            processor.process_webcam()
            logger.info("Webcam session completed.")
            print("\n✅ Webcam movement analysis session completed.\n")
        else:
            logger.info(f"Opening video: {args.source}")
            session_stats = processor.process_video_file()

            # Generate reports
            logger.info("Generating reports...")
            reporter = MovementReportGenerator(config.reports_dir, logger=logger)
            s_path, p_path, zv_path, t_path, md_path = reporter.generate(
                session_stats=session_stats,
                session_manager=session_manager,
                path_tracker=path_tracker,
                zone_tracker=zone_tracker,
            )

            logger.info("Done.")

            # Print summary
            border = "═" * 65
            print(f"\n{border}")
            print("  MOVEMENT ANALYSIS — SESSION SUMMARY")
            print(border)
            print(f"  {'Video':<32} : {session_stats['video_filename']}")
            print(f"  {'Resolution':<32} : {session_stats['video_resolution']}")
            print(f"  {'Duration':<32} : {session_stats['video_duration_sec']}s")
            print(f"  {'Frames Processed':<32} : {session_stats['total_frames_processed']:,}")
            print(f"  {'Total Unique Shoppers':<32} : {session_stats['total_unique_shoppers']}")
            print(f"  {'Total Entries':<32} : {session_stats['total_entries']}")
            print(f"  {'Total Exits':<32} : {session_stats['total_exits']}")
            print(f"  {'Track Lost':<32} : {session_stats['total_track_lost']}")
            print(f"  {'Max Simultaneous Shoppers':<32} : {session_stats['max_simultaneous_shoppers']}")
            print(f"  {'Avg Active Shoppers':<32} : {session_stats['average_active_shoppers']:.2f}")
            print(f"  {'Processing FPS':<32} : {session_stats['processing_fps']:.2f}")
            print(f"  {'Device':<32} : {session_stats['device']}")
            print(f"  {'─' * 63}")
            print(f"  {'Annotated Video':<32} : {session_stats['output_video']}")
            print(f"  {'Sessions Report':<32} : {s_path}")
            print(f"  {'Paths Report':<32} : {p_path}")
            print(f"  {'Zone Visits Report':<32} : {zv_path}")
            print(f"  {'Traffic Summary':<32} : {t_path}")
            print(f"  {'Movement Report':<32} : {md_path}")
            print(border)
            print("\n✅ Movement analysis completed successfully.\n")

    except FileNotFoundError as exc:
        logger.error(str(exc))
        print(f"\n❌ File error: {exc}\n")
        return 1
    except RuntimeError as exc:
        logger.error(str(exc))
        print(f"\n❌ Runtime error: {exc}\n")
        return 1
    except MemoryError:
        logger.error("Out of memory. Try reducing IMAGE_SIZE in .env.")
        print("\n❌ Out of memory. Try reducing IMAGE_SIZE in .env.\n")
        return 1
    except PermissionError as exc:
        logger.error(f"Permission denied: {exc}")
        print(f"\n❌ Permission error: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
