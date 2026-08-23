"""
AI Module — Pretrained YOLO Inference (CLI Entry Point)
========================================================
Loads the pretrained YOLOv8 model (no training) and runs inference
on a sample of COCO val2017 images.

Usage::

    python ai/coco/inference.py

Outputs:
- Annotated prediction images → ai/coco/outputs/inference/
- Detection summary JSON      → ai/coco/outputs/inference/inference_report.json
"""

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import load_config
from ai.dataset import get_random_val_images
from ai.utils import ensure_directory, get_device, print_banner, setup_logger, timer

logger = setup_logger(__name__)

# Number of sample images to run inference on
NUM_SAMPLES = 5


def main() -> int:
    """
    Run pretrained YOLO inference on sample COCO images.

    Returns
    -------
    int
        0 on success, 1 on failure.
    """
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — YOLO Inference")

    # ── Configuration ─────────────────────────────────────────
    logger.info("Loading Environment...")
    try:
        config = load_config()
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    device = get_device(config.device)
    coco_output_base = Path(__file__).resolve().parent / "outputs"
    output_dir = ensure_directory(coco_output_base / "inference")

    logger.info(f"  Model       : {config.yolo_model_name}")
    logger.info(f"  Device      : {device}")
    logger.info(f"  Image Size  : {config.image_size}")
    logger.info(f"  Output Dir  : {output_dir}")
    print()

    # ── Load model ────────────────────────────────────────────
    try:
        # pyrefly: ignore [missing-import]
        from ultralytics import YOLO
    except ImportError:
        logger.error(
            "Ultralytics is not installed. Run: pip install -r ai/requirements.txt"
        )
        return 1

    logger.info("Loading YOLO...")
    with timer("Model loading", logger):
        try:
            model = YOLO(config.yolo_model_name)
        except Exception as exc:
            logger.error(f"Failed to load YOLO model '{config.yolo_model_name}': {exc}")
            return 1
    logger.info(f"Model loaded: {config.yolo_model_name}")
    print()

    # ── Sample images ─────────────────────────────────────────
    logger.info("Loading Dataset...")
    try:
        images = get_random_val_images(config, n=NUM_SAMPLES)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1
    logger.info(f"Selected {len(images)} images for inference")
    print()

    # ── Run inference ─────────────────────────────────────────
    logger.info("Running Inference...")
    all_results = []

    for idx, image_path in enumerate(images, 1):
        logger.info(f"  [{idx}/{len(images)}] Processing: {image_path.name}")

        with timer(f"  Inference on {image_path.name}", logger):
            try:
                results = model.predict(
                    source=str(image_path),
                    imgsz=config.image_size,
                    device=device,
                    save=True,
                    project=str(output_dir),
                    name="predictions",
                    exist_ok=True,
                    verbose=False,
                )
            except PermissionError as exc:
                logger.error(f"Permission denied writing output: {exc}")
                return 1
            except Exception as exc:
                logger.error(f"Inference failed on {image_path.name}: {exc}")
                continue

        # Parse results
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes
            detections = []

            if boxes is not None and len(boxes) > 0:
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    conf = float(boxes.conf[i].item())
                    class_name = result.names.get(cls_id, f"class_{cls_id}")
                    detections.append({
                        "class": class_name,
                        "class_id": cls_id,
                        "confidence": round(conf, 4),
                    })

            image_report = {
                "image": image_path.name,
                "num_detections": len(detections),
                "detections": detections,
                "inference_time_ms": round(
                    (result.speed.get("inference", 0)), 2
                ) if hasattr(result, "speed") and result.speed else None,
            }
            all_results.append(image_report)

            # Log detections
            logger.info(f"    Detected {len(detections)} object(s)")
            for det in detections[:10]:  # Show top 10
                logger.info(
                    f"      • {det['class']:20s}  confidence: {det['confidence']:.4f}"
                )
            if len(detections) > 10:
                logger.info(f"      ... and {len(detections) - 10} more")
        print()

    # ── Save summary report ───────────────────────────────────
    report_path = output_dir / "inference_report.json"
    summary = {
        "model": config.yolo_model_name,
        "device": device,
        "image_size": config.image_size,
        "num_images": len(images),
        "results": all_results,
    }

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Inference report saved: {report_path}")
    except (PermissionError, OSError) as exc:
        logger.error(f"Failed to save report: {exc}")

    print_banner("Inference Successful")
    logger.info(f"Prediction images saved to: {output_dir / 'predictions'}")
    logger.info(f"Summary report saved to:    {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
