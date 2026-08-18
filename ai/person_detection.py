"""
Module 3 — Phase 1: Person Detection Pipeline (CLI Entry Point)
================================================================
Independent computer-vision pipeline that reads video files or webcam
input, runs YOLOv8 person detection, and generates annotated output.

Usage:
    # Video file
    python ai/person_detection.py --source /path/to/video.mp4

    # Webcam (default camera)
    python ai/person_detection.py --source 0

    # With optional overrides
    python ai/person_detection.py --source /path/to/video.mp4 --confidence 0.50 --save-frames

Pipeline:
    Input (Video/Webcam) → OpenCV → YOLOv8 → Person Detection → Annotated Output + Report
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
        description="Module 3 Phase 1 — Person Detection Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai/person_detection.py --source /path/to/video.mp4
  python ai/person_detection.py --source 0
  python ai/person_detection.py --source /path/to/video.mp4 --confidence 0.50
  python ai/person_detection.py --source /path/to/video.mp4 --save-frames
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
        help="Override SAVE_FRAMES: save annotated frames with person detections",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output base directory",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for the person detection pipeline."""
    args = parse_args()

    # ── Imports after sys.path setup ──────────────────────────────
    from ai.person_detection.config import (
        PersonDetectionConfig,
        load_person_detection_config,
    )
    from ai.person_detection.detector import PersonDetector
    from ai.person_detection.video_processor import VideoProcessor
    from ai.person_detection.report import ReportGenerator
    from ai.logger import setup_logger
    from ai.utils import ensure_directory, print_banner

    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — Person Detection (Module 3, Phase 1)")

    # ── Load configuration ───────────────────────────────────────
    try:
        config = load_person_detection_config()
    except Exception as exc:
        print(f"\n❌ Configuration error: {exc}\n")
        return 1

    # ── Apply CLI overrides ──────────────────────────────────────
    overrides = {}
    if args.confidence is not None:
        if not 0.0 <= args.confidence <= 1.0:
            print(f"\n❌ Invalid confidence value: {args.confidence}. Must be between 0.0 and 1.0.\n")
            return 1
        overrides["confidence_threshold"] = args.confidence

    if args.save_frames is not None:
        overrides["save_frames"] = args.save_frames

    if args.output_dir is not None:
        output_base = Path(args.output_dir)
        if not output_base.is_absolute():
            output_base = _PROJECT_ROOT / output_base
        overrides["output_base"] = output_base
        overrides["videos_dir"] = output_base / "videos"
        overrides["frames_dir"] = output_base / "frames"
        overrides["reports_dir"] = output_base / "reports"
        overrides["logs_dir"] = output_base / "logs"

    # Rebuild config with overrides if needed
    if overrides:
        config_dict = {
            "person_model_path": config.person_model_path,
            "confidence_threshold": config.confidence_threshold,
            "image_size": config.image_size,
            "device": config.device,
            "save_frames": config.save_frames,
            "output_base": config.output_base,
            "videos_dir": config.videos_dir,
            "frames_dir": config.frames_dir,
            "reports_dir": config.reports_dir,
            "logs_dir": config.logs_dir,
        }
        config_dict.update(overrides)
        config = PersonDetectionConfig(**config_dict)

    # ── Setup logging to file ────────────────────────────────────
    log_dir = ensure_directory(config.logs_dir)
    log_file = log_dir / "person_detection.log"
    logger = setup_logger("person_detection", log_file=log_file)

    logger.info("Loading configuration...")
    logger.info(f"  Model path              : {config.person_model_path}")
    logger.info(f"  Confidence threshold    : {config.confidence_threshold}")
    logger.info(f"  Image size              : {config.image_size}")
    logger.info(f"  Device preference       : {config.device}")
    logger.info(f"  Save frames             : {config.save_frames}")
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

    # ── Initialize detector ──────────────────────────────────────
    try:
        logger.info("Loading person detection model...")
        detector = PersonDetector(config, logger=logger)
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

    # ── Initialize video processor ───────────────────────────────
    processor = VideoProcessor(
        source=args.source,
        config=config,
        detector=detector,
        logger=logger,
    )

    # ── Process ──────────────────────────────────────────────────
    try:
        if is_webcam:
            processor.process_webcam()
            logger.info("Done.")
            print("\n✅ Webcam session completed.\n")
        else:
            logger.info(f"Opening video: {args.source}")
            session_stats = processor.process_video_file()

            # Generate reports
            logger.info("Generating report...")
            reporter = ReportGenerator(config.reports_dir, logger=logger)
            json_path, md_path = reporter.generate(session_stats)

            logger.info("Done.")

            # Print summary
            border = "═" * 60
            print(f"\n{border}")
            print("  PERSON DETECTION — SESSION SUMMARY")
            print(border)
            print(f"  {'Video':<25} : {session_stats['video_filename']}")
            print(f"  {'Resolution':<25} : {session_stats['video_resolution']}")
            print(f"  {'Duration':<25} : {session_stats['video_duration_sec']}s")
            print(f"  {'Frames Processed':<25} : {session_stats['total_frames_processed']:,}")
            print(f"  {'Frames with Persons':<25} : {session_stats['total_frames_with_persons']:,}")
            print(f"  {'Total Detections':<25} : {session_stats['total_person_detections']:,}")
            print(f"  {'Avg Inference Time':<25} : {session_stats['average_inference_time_ms']:.2f} ms")
            print(f"  {'Avg Confidence':<25} : {session_stats['average_confidence']:.4f}")
            print(f"  {'Effective FPS':<25} : {session_stats['effective_fps']:.2f}")
            print(f"  {'Device':<25} : {session_stats['device']}")
            print(f"  {'─' * 58}")
            print(f"  {'Output Video':<25} : {session_stats['output_video']}")
            print(f"  {'JSON Report':<25} : {json_path}")
            print(f"  {'Markdown Report':<25} : {md_path}")
            print(border)
            print("\n✅ Person detection completed successfully.\n")

    except FileNotFoundError as exc:
        logger.error(str(exc))
        print(f"\n❌ File error: {exc}\n")
        return 1
    except RuntimeError as exc:
        logger.error(str(exc))
        print(f"\n❌ Runtime error: {exc}\n")
        return 1
    except MemoryError:
        logger.error("Out of memory. Try reducing IMAGE_SIZE or using a shorter video.")
        print("\n❌ Out of memory. Try reducing IMAGE_SIZE in .env.\n")
        return 1
    except PermissionError as exc:
        logger.error(f"Permission denied: {exc}")
        print(f"\n❌ Permission error: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
