"""
Module 3 — Phase 2: Multi-Person Tracking Pipeline (CLI Entry Point)
=====================================================================
Independent computer-vision pipeline that consumes video files or webcam streams,
runs YOLOv8 person detection, applies ByteTrack for persistent multi-person tracking,
renders annotated output video, and generates structured tracking reports.

Usage:
    # Video file
    python ai/person_tracking.py --source /path/to/video.mp4

    # Webcam (default camera)
    python ai/person_tracking.py --source 0

    # With CLI overrides
    python ai/person_tracking.py --source /path/to/video.mp4 --confidence 0.40 --save-frames

Pipeline:
    Video/Webcam -> OpenCV -> YOLOv8 Person Detection -> ByteTrack -> Persistent IDs -> Annotated Video + Tracking Report
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
        description="Module 3 Phase 2 — Multi-Person Tracking Pipeline (ByteTrack)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai/person_tracking.py --source /path/to/video.mp4
  python ai/person_tracking.py --source 0
  python ai/person_tracking.py --source /path/to/video.mp4 --confidence 0.50
  python ai/person_tracking.py --source /path/to/video.mp4 --save-frames
        """,
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to video file or webcam index (e.g., 0 for default webcam)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="Override PERSON_CONFIDENCE_THRESHOLD from .env (0.0 - 1.0)",
    )
    parser.add_argument(
        "--save-frames",
        action="store_true",
        default=None,
        help="Override SAVE_FRAMES: save individual annotated frames with active tracks",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output base directory for Phase 2 artifacts",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for the person tracking pipeline."""
    args = parse_args()

    # ── Imports after sys.path setup ──────────────────────────────
    from ai.logger import setup_logger
    from ai.person_detection.config import PersonDetectionConfig
    from ai.person_detection.detector import PersonDetector
    from ai.person_tracking.config import (
        PersonTrackingConfig,
        load_person_tracking_config,
    )
    from ai.person_tracking.report import TrackingReportGenerator
    from ai.person_tracking.tracker import PersonTracker
    from ai.person_tracking.video_processor import TrackingVideoProcessor
    from ai.person_tracking.visualizer import TrackVisualizer
    from ai.utils import ensure_directory, print_banner

    print_banner(
        "CONSUMER ATTENTION MAPPING SYSTEM — Multi-Person Tracking (Module 3, Phase 2)"
    )

    # ── Load configuration ───────────────────────────────────────
    try:
        config = load_person_tracking_config()
    except Exception as exc:
        print(f"\n❌ Configuration error: {exc}\n")
        return 1

    # ── Apply CLI overrides ──────────────────────────────────────
    if args.confidence is not None or args.save_frames is not None or args.output_dir is not None:
        det_conf = config.detection_config
        conf_thresh = args.confidence if args.confidence is not None else det_conf.confidence_threshold
        save_frames = args.save_frames if args.save_frames is not None else det_conf.save_frames

        if not 0.0 <= conf_thresh <= 1.0:
            print(f"\n❌ Invalid confidence value: {conf_thresh}. Must be between 0.0 and 1.0.\n")
            return 1

        output_base = config.output_base
        if args.output_dir is not None:
            output_base = Path(args.output_dir)
            if not output_base.is_absolute():
                output_base = _PROJECT_ROOT / output_base

        videos_dir = output_base / "videos"
        frames_dir = output_base / "frames"
        reports_dir = output_base / "reports"
        logs_dir = output_base / "logs"

        new_detection_config = PersonDetectionConfig(
            person_model_path=det_conf.person_model_path,
            confidence_threshold=conf_thresh,
            image_size=det_conf.image_size,
            device=det_conf.device,
            save_frames=save_frames,
            output_base=det_conf.output_base,
            videos_dir=det_conf.videos_dir,
            frames_dir=det_conf.frames_dir,
            reports_dir=det_conf.reports_dir,
            logs_dir=det_conf.logs_dir,
        )

        config = PersonTrackingConfig(
            detection_config=new_detection_config,
            track_high_threshold=config.track_high_threshold,
            track_low_threshold=config.track_low_threshold,
            new_track_threshold=config.new_track_threshold,
            track_buffer=config.track_buffer,
            match_threshold=config.match_threshold,
            trajectory_enabled=config.trajectory_enabled,
            trajectory_length=config.trajectory_length,
            output_base=output_base,
            videos_dir=videos_dir,
            frames_dir=frames_dir,
            reports_dir=reports_dir,
            logs_dir=logs_dir,
        )

    # ── Setup logging to file ────────────────────────────────────
    log_dir = ensure_directory(config.logs_dir)
    log_file = log_dir / "person_tracking.log"
    logger = setup_logger("person_tracking", log_file=log_file)

    logger.info("Loading configuration...")
    logger.info(f"  Model path              : {config.detection_config.person_model_path}")
    logger.info(f"  Confidence threshold    : {config.detection_config.confidence_threshold}")
    logger.info(f"  Tracker                 : ByteTrack")
    logger.info(f"  Track High Threshold    : {config.track_high_threshold}")
    logger.info(f"  Track Low Threshold     : {config.track_low_threshold}")
    logger.info(f"  New Track Threshold     : {config.new_track_threshold}")
    logger.info(f"  Track Buffer (frames)   : {config.track_buffer}")
    logger.info(f"  Match Threshold (IoU)   : {config.match_threshold}")
    logger.info(f"  Trajectory Visualization: {config.trajectory_enabled}")
    logger.info(f"  Output directory        : {config.output_base}")

    # ── Determine source type ────────────────────────────────────
    is_webcam = False
    try:
        int(args.source)
        is_webcam = True
    except (ValueError, TypeError):
        pass

    source_label = f"Webcam (index {args.source})" if is_webcam else args.source
    logger.info(f"  Source                  : {source_label}")

    # ── Initialize detector (Phase 1 reuse) ──────────────────────
    try:
        logger.info("Loading YOLOv8 person detection model...")
        detector = PersonDetector(config.detection_config, logger=logger)
    except FileNotFoundError as exc:
        logger.error(f"Model not found: {exc}")
        print(f"\n❌ Model error: {exc}\n")
        return 1
    except ValueError as exc:
        logger.error(f"Model validation failed: {exc}")
        print(f"\n❌ Model validation error:\n{exc}\n")
        return 1
    except RuntimeError as exc:
        logger.error(f"Model loading failed: {exc}")
        print(f"\n❌ Model error: {exc}\n")
        return 1

    # ── Initialize ByteTrack tracker ─────────────────────────────
    logger.info("Initializing ByteTrack...")
    tracker = PersonTracker(config=config, logger=logger)
    logger.info("ByteTrack initialized.")

    # ── Initialize visualizer and video processor ────────────────
    visualizer = TrackVisualizer(config=config)
    processor = TrackingVideoProcessor(
        source=args.source,
        config=config,
        detector=detector,
        tracker=tracker,
        visualizer=visualizer,
        logger=logger,
    )

    # ── Execute ──────────────────────────────────────────────────
    try:
        if is_webcam:
            processor.process_webcam()
            logger.info("Webcam tracking session completed.")
            print("\n✅ Webcam tracking session completed.\n")
        else:
            logger.info(f"Opening video: {args.source}")
            session_stats, frame_records = processor.process_video_file()

            # Generate reports
            logger.info("Generating tracking reports...")
            reporter = TrackingReportGenerator(config.reports_dir, logger=logger)
            json_path, md_path, tracks_json_path = reporter.generate(
                session_stats=session_stats,
                track_history=tracker.track_history,
                frame_tracking_records=frame_records,
            )

            logger.info("Done.")

            # Print concise execution summary
            border = "═" * 65
            print(f"\n{border}")
            print("  MULTI-PERSON TRACKING (BYTETrack) — SESSION SUMMARY")
            print(border)
            print(f"  {'Video':<32} : {session_stats['video_filename']}")
            print(f"  {'Resolution':<32} : {session_stats['video_resolution']}")
            print(f"  {'Duration':<32} : {session_stats['video_duration_sec']}s")
            print(f"  {'Frames Processed':<32} : {session_stats['total_frames_processed']:,}")
            print(f"  {'Total Person Detections':<32} : {session_stats['total_person_detections']:,}")
            print(f"  {'Total Unique Track IDs':<32} : {session_stats['total_unique_tracking_ids']}")
            print(f"  {'Max Simultaneous People':<32} : {session_stats['max_simultaneous_tracked_people']}")
            print(f"  {'Avg Active Tracks / Frame':<32} : {session_stats['average_active_tracks']:.2f}")
            print(f"  {'Avg Tracking Confidence':<32} : {session_stats['average_tracking_confidence']:.4f}")
            print(f"  {'YOLO Inference Time':<32} : {session_stats['average_yolo_inference_time_ms']:.2f} ms")
            print(f"  {'ByteTrack Processing Time':<32} : {session_stats['average_bytetrack_time_ms']:.2f} ms")
            print(f"  {'Processing FPS':<32} : {session_stats['processing_fps']:.2f} FPS")
            print(f"  {'Device':<32} : {session_stats['device']}")
            print(f"  {'─' * 63}")
            print(f"  {'Annotated Video':<32} : {session_stats['output_video']}")
            print(f"  {'Summary JSON Report':<32} : {json_path}")
            print(f"  {'Summary Markdown Report':<32} : {md_path}")
            print(f"  {'Frame Tracks Data':<32} : {tracks_json_path}")
            print(border)
            print("\n✅ Multi-person tracking completed successfully.\n")

    except FileNotFoundError as exc:
        logger.error(str(exc))
        print(f"\n❌ File error: {exc}\n")
        return 1
    except RuntimeError as exc:
        logger.error(str(exc))
        print(f"\n❌ Runtime error: {exc}\n")
        return 1
    except MemoryError:
        logger.error("Out of memory error. Try reducing IMAGE_SIZE in .env.")
        print("\n❌ Out of memory error. Try reducing IMAGE_SIZE in .env.\n")
        return 1
    except PermissionError as exc:
        logger.error(f"Permission denied: {exc}")
        print(f"\n❌ Permission error: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
