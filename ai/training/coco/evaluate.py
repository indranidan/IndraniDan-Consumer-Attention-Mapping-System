"""
AI Module — Pretrained YOLO Evaluation (CLI Entry Point)
==========================================================
Evaluates the pretrained YOLOv8 model on COCO val2017.

This does **NOT** train or modify the model weights.
It only measures baseline performance metrics.

Usage::

    python ai/coco/evaluate.py

Outputs:
- Precision, Recall, mAP50, mAP50-95
- Confusion matrix (if supported by Ultralytics)
- Evaluation report (text + JSON) → ai/coco/outputs/evaluation/
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import yaml

from ai.config import load_config
from ai.dataset import resolve_coco_paths, validate_coco_dataset
from ai.utils import ensure_directory, get_device, print_banner, setup_logger, timer

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# COCO data YAML generator
# ---------------------------------------------------------------------------
def _generate_coco_data_yaml(
    val_images_dir: Path,
    output_dir: Path,
    train_images_dir: Optional[Path] = None,
) -> Path:
    """
    Generate a minimal COCO data YAML for Ultralytics ``model.val()``.

    Ultralytics expects a YAML with ``path``, ``train``, ``val``, and ``names``.
    We point it directly at the resolved val2017 images directory.

    Parameters
    ----------
    val_images_dir : Path
        Resolved path to the actual val2017 images.
    output_dir : Path
        Directory to write the YAML into.
    train_images_dir : Path, optional
        Resolved path to the train2017 images if available.

    Returns
    -------
    Path
        Path to the generated YAML file.
    """
    # COCO 80-class names used by YOLOv8 pretrained weights
    coco_names = {
        0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
        5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
        10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
        14: "bird", 15: "cat", 16: "dog", 17: "elephant", 18: "bear",
        19: "zebra", 20: "giraffe", 21: "backpack", 22: "umbrella",
        23: "handbag", 24: "tie", 25: "suitcase", 26: "frisbee", 27: "skis",
        28: "snowboard", 29: "sports ball", 30: "kite", 31: "baseball bat",
        32: "baseball glove", 33: "skateboard", 34: "surfboard",
        35: "tennis racket", 36: "bottle", 37: "wine glass", 38: "cup",
        39: "fork", 40: "knife", 41: "spoon", 42: "bowl", 43: "banana",
        44: "apple", 45: "sandwich", 46: "orange", 47: "broccoli",
        48: "carrot", 49: "hot dog", 50: "pizza", 51: "donut", 52: "cake",
        53: "chair", 54: "couch", 55: "potted plant", 56: "bed",
        57: "dining table", 58: "toilet", 59: "tv", 60: "laptop",
        61: "mouse", 62: "remote", 63: "keyboard", 64: "cell phone",
        65: "microwave", 66: "oven", 67: "toaster", 68: "sink",
        69: "refrigerator", 70: "book", 71: "clock", 72: "vase",
        73: "scissors", 74: "teddy bear", 75: "hair drier", 76: "toothbrush",
    }

    # Ultralytics val expects path + train + val (relative to path)
    train_path = (
        train_images_dir.name
        if train_images_dir and train_images_dir.parent == val_images_dir.parent
        else val_images_dir.name
    )

    data_config = {
        "path": str(val_images_dir.parent),
        "train": train_path,
        "val": val_images_dir.name,
        "names": coco_names,
    }

    yaml_path = output_dir / "coco_val_data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_config, f, default_flow_style=False, allow_unicode=True)

    logger.info(f"Generated data YAML: {yaml_path}")
    return yaml_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    """
    Evaluate the pretrained YOLO model on COCO val2017.

    Returns
    -------
    int
        0 on success, 1 on failure.
    """
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — YOLO Evaluation")

    # ── Configuration ─────────────────────────────────────────
    logger.info("Loading Environment...")
    try:
        config = load_config()
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    device = get_device(config.device)
    coco_output_base = Path(__file__).resolve().parent / "outputs"
    eval_dir = ensure_directory(coco_output_base / "evaluation")

    logger.info(f"  Model          : {config.yolo_model_name}")
    logger.info(f"  Device         : {device}")
    logger.info(f"  Image Size     : {config.image_size}")
    logger.info(f"  Max Samples    : {config.max_eval_samples or 'ALL'}")
    logger.info(f"  Output Dir     : {eval_dir}")
    print()

    # ── Validate dataset first ────────────────────────────────
    logger.info("Loading Dataset...")
    coco_report = validate_coco_dataset(config)
    if not coco_report.passed:
        logger.error("COCO dataset validation failed. Run verify_dataset.py first.")
        print(coco_report.summary())
        return 1
    logger.info("Dataset Verified")

    # Resolve paths
    paths = resolve_coco_paths(config.coco_dataset_path)
    if paths is None:
        logger.error("Failed to resolve COCO paths")
        return 1

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
            logger.error(f"Failed to load model '{config.yolo_model_name}': {exc}")
            return 1
    logger.info(f"Model loaded: {config.yolo_model_name}")
    print()

    # ── Generate data YAML ────────────────────────────────────
    logger.info("Preparing evaluation configuration...")
    try:
        data_yaml = _generate_coco_data_yaml(
            val_images_dir=paths.val_images,
            output_dir=eval_dir,
            train_images_dir=paths.train_images,
        )
    except (PermissionError, OSError) as exc:
        logger.error(f"Failed to generate data YAML: {exc}")
        return 1

    # ── Run evaluation ────────────────────────────────────────
    logger.info("Evaluating Model...")
    print()

    val_kwargs = {
        "data": str(data_yaml),
        "imgsz": config.image_size,
        "device": device,
        "verbose": True,
        "project": str(eval_dir),
        "name": "results",
        "exist_ok": True,
        "save_json": False,
        "plots": True,  # Generate confusion matrix + other plots
    }

    # Limit samples if configured (for low-RAM systems)
    if config.max_eval_samples > 0:
        val_kwargs["max_det"] = 300  # default
        logger.info(
            f"  ⚠ Limiting evaluation to {config.max_eval_samples} images "
            f"(MAX_EVAL_SAMPLES={config.max_eval_samples})"
        )

    with timer("Model evaluation", logger):
        try:
            metrics = model.val(**val_kwargs)
        except PermissionError as exc:
            logger.error(f"Permission denied during evaluation: {exc}")
            return 1
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                logger.error(
                    "Out of memory! Reduce MAX_EVAL_SAMPLES in .env "
                    f"(currently {config.max_eval_samples})"
                )
            else:
                logger.error(f"Runtime error during evaluation: {exc}")
            return 1
        except Exception as exc:
            logger.error(f"Evaluation failed: {exc}")
            return 1

    print()
    logger.info("Evaluation Complete")
    print()

    # ── Extract metrics ───────────────────────────────────────
    try:
        precision = float(metrics.box.mp) if hasattr(metrics.box, "mp") else None
        recall = float(metrics.box.mr) if hasattr(metrics.box, "mr") else None
        map50 = float(metrics.box.map50) if hasattr(metrics.box, "map50") else None
        map50_95 = float(metrics.box.map) if hasattr(metrics.box, "map") else None
    except Exception as exc:
        logger.warning(f"Could not extract some metrics: {exc}")
        precision = recall = map50 = map50_95 = None

    # ── Display results ───────────────────────────────────────
    print_banner("Evaluation Results")

    results_table = [
        ("Precision", precision),
        ("Recall", recall),
        ("mAP@0.5", map50),
        ("mAP@0.5:0.95", map50_95),
    ]

    for name, value in results_table:
        if value is not None:
            logger.info(f"  {name:20s}: {value:.4f}")
        else:
            logger.info(f"  {name:20s}: N/A")
    print()

    # ── Save reports ──────────────────────────────────────────
    # JSON report
    report_data = {
        "model": config.yolo_model_name,
        "device": device,
        "image_size": config.image_size,
        "max_eval_samples": config.max_eval_samples,
        "metrics": {
            "precision": round(precision, 6) if precision is not None else None,
            "recall": round(recall, 6) if recall is not None else None,
            "mAP50": round(map50, 6) if map50 is not None else None,
            "mAP50_95": round(map50_95, 6) if map50_95 is not None else None,
        },
    }

    json_path = eval_dir / "evaluation_report.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON report saved: {json_path}")
    except (PermissionError, OSError) as exc:
        logger.error(f"Failed to save JSON report: {exc}")

    # Text report
    text_path = eval_dir / "evaluation_report.txt"
    try:
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("  YOLO Pretrained Model — Evaluation Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Model          : {config.yolo_model_name}\n")
            f.write(f"Device         : {device}\n")
            f.write(f"Image Size     : {config.image_size}\n")
            f.write(f"Max Samples    : {config.max_eval_samples or 'ALL'}\n\n")
            f.write("-" * 40 + "\n")
            f.write("  Metrics\n")
            f.write("-" * 40 + "\n\n")
            for name, value in results_table:
                val_str = f"{value:.6f}" if value is not None else "N/A"
                f.write(f"  {name:20s}: {val_str}\n")
            f.write("\n" + "=" * 60 + "\n")
        logger.info(f"Text report saved: {text_path}")
    except (PermissionError, OSError) as exc:
        logger.error(f"Failed to save text report: {exc}")

    # ── Copy confusion matrix if generated ────────────────────
    results_dir = eval_dir / "results"
    if results_dir.is_dir():
        for plot_file in results_dir.glob("*.png"):
            dest = eval_dir / plot_file.name
            try:
                shutil.copy2(plot_file, dest)
                logger.info(f"Plot saved: {dest}")
            except (PermissionError, OSError) as exc:
                logger.warning(f"Could not copy plot {plot_file.name}: {exc}")

    print()
    print_banner("Evaluation Complete")
    logger.info(f"All outputs saved to: {eval_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
