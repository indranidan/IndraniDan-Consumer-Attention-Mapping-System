"""
SKU-110K Evaluation Utilities
==============================
Helper functions for model evaluation, report generation, and visualization.
"""

import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import yaml

matplotlib.use("Agg")

# Plot style matching training_utils.py
PLOT_STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.edgecolor": "#e94560",
    "axes.labelcolor": "#e0e0e0",
    "text.color": "#e0e0e0",
    "xtick.color": "#e0e0e0",
    "ytick.color": "#e0e0e0",
    "grid.color": "#2a2a4a",
    "grid.alpha": 0.5,
    "font.size": 11,
}


def setup_eval_directories(base: Path, clean_existing: bool = True) -> Dict[str, Path]:
    """Create evaluation output directory structure, clearing previous contents if requested."""
    if clean_existing and base.exists():
        for item in base.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink()
                except Exception:
                    pass
    base.mkdir(parents=True, exist_ok=True)
    dirs = {
        "root": base,
        "inference": base / "inference",
        "plots": base / "plots",
        "reports": base / "reports",
        "exported_models": base / "exported_models",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def get_model_info(model: Any, model_path: Path, device: str) -> Dict[str, Any]:
    """Extract model metadata for reporting."""
    size_mb = model_path.stat().st_size / (1024 * 1024)
    names = getattr(model, "names", {})
    nc = len(names) if names else 0
    return {
        "model_path": str(model_path),
        "model_size_mb": round(size_mb, 2),
        "yolo_version": "YOLOv8 (Ultralytics)",
        "num_classes": nc,
        "class_names": list(names.values()) if names else [],
        "device": device,
    }


def run_validation(
    model: Any,
    data_yaml: str,
    imgsz: int,
    device: str,
    project: str,
    name: str,
    conf: float = 0.25,
) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    """Run model.val() and return extracted metrics dict + run directory."""
    start = time.perf_counter()
    try:
        metrics = model.val(
            data=data_yaml,
            imgsz=imgsz,
            device=device,
            verbose=True,
            project=project,
            name=name,
            exist_ok=True,
            save_json=False,
            plots=True,
            conf=conf,
        )
    except Exception as exc:
        return None, None
    elapsed = time.perf_counter() - start

    result: Dict[str, Any] = {"evaluation_time_seconds": round(elapsed, 2)}
    try:
        result["precision"] = round(float(metrics.box.mp), 6)
        result["recall"] = round(float(metrics.box.mr), 6)
        result["mAP50"] = round(float(metrics.box.map50), 6)
        result["mAP50_95"] = round(float(metrics.box.map), 6)
    except Exception:
        pass

    try:
        speed = metrics.speed
        if speed:
            result["inference_speed_ms"] = round(speed.get("inference", 0), 2)
            result["preprocess_ms"] = round(speed.get("preprocess", 0), 2)
            result["postprocess_ms"] = round(speed.get("postprocess", 0), 2)
    except Exception:
        pass

    run_dir = Path(project) / name
    return result, run_dir if run_dir.exists() else None


def create_test_yaml(
    original_yaml: Path, test_split: str, output_dir: Path
) -> Optional[Path]:
    """Create a temporary YAML pointing val to the test split for test evaluation."""
    try:
        with open(original_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "test" not in data:
            return None
        dataset_root = Path(data["path"])
        test_dir = dataset_root / data["test"]
        if not test_dir.exists() or not any(test_dir.iterdir()):
            return None
        test_data = dict(data)
        test_data["val"] = data["test"]
        yaml_path = output_dir / "sku110k_test_data.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(test_data, f, default_flow_style=False)
        return yaml_path
    except Exception:
        return None


def count_dataset_images(yaml_path: Path, split: str = "val") -> int:
    """Count images in a dataset split."""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        root = Path(data["path"])
        split_dir = root / data.get(split, "")
        if split_dir.exists():
            exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
            return sum(1 for f in split_dir.iterdir() if f.suffix.lower() in exts)
    except Exception:
        pass
    return 0


def run_sample_inference(
    model: Any,
    yaml_path: Path,
    sample_count: int,
    imgsz: int,
    device: str,
    conf: float,
    output_dir: Path,
) -> List[Dict[str, Any]]:
    """Run inference on sample images and return detection results."""
    import random

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    root = Path(data["path"])
    val_dir = root / data.get("val", "")
    if not val_dir.exists():
        return []

    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_images = [f for f in val_dir.iterdir() if f.suffix.lower() in exts]
    if not all_images:
        return []

    samples = random.sample(all_images, min(sample_count, len(all_images)))
    results_list: List[Dict[str, Any]] = []

    for img_path in samples:
        start = time.perf_counter()
        try:
            results = model.predict(
                source=str(img_path),
                imgsz=imgsz,
                device=device,
                conf=conf,
                save=True,
                project=str(output_dir),
                name="predictions",
                exist_ok=True,
                verbose=False,
            )
        except Exception:
            continue
        inf_time = round((time.perf_counter() - start) * 1000, 2)

        if not results or len(results) == 0:
            continue

        result = results[0]
        boxes = result.boxes
        detections = []
        if boxes is not None and len(boxes) > 0:
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                c = float(boxes.conf[i].item())
                detections.append({
                    "class": result.names.get(cls_id, f"class_{cls_id}"),
                    "class_id": cls_id,
                    "confidence": round(c, 4),
                })

        results_list.append({
            "image": img_path.name,
            "num_detections": len(detections),
            "detected_classes": list({d["class"] for d in detections}),
            "confidence_scores": [d["confidence"] for d in detections],
            "inference_time_ms": inf_time,
        })

    # Move predictions to inference root
    pred_dir = output_dir / "predictions"
    if pred_dir.exists():
        for f in pred_dir.iterdir():
            if f.is_file():
                shutil.move(str(f), str(output_dir / f.name))
        try:
            pred_dir.rmdir()
        except OSError:
            pass

    return results_list


def copy_ultralytics_plots(run_dir: Optional[Path], plots_dir: Path) -> int:
    """Copy Ultralytics-generated plots from val run directory."""
    if not run_dir or not run_dir.exists():
        return 0
    copied = 0
    for f in run_dir.iterdir():
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            dest = plots_dir / f.name
            shutil.copy2(f, dest)
            copied += 1
    return copied


def generate_confidence_plot(
    detection_results: List[Dict[str, Any]], plots_dir: Path
) -> Optional[Path]:
    """Generate a confidence score distribution plot from sample inference."""
    all_confs = []
    for r in detection_results:
        all_confs.extend(r.get("confidence_scores", []))
    if not all_confs:
        return None

    plt.rcParams.update(PLOT_STYLE)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(all_confs, bins=30, color="#53d8fb", edgecolor="#1a1a2e", alpha=0.85)
    ax.set_xlabel("Confidence Score")
    ax.set_ylabel("Frequency")
    ax.set_title("Detection Confidence Distribution", fontsize=14, fontweight="bold")
    ax.grid(True)
    path = plots_dir / "confidence_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_detections_per_image_plot(
    detection_results: List[Dict[str, Any]], plots_dir: Path
) -> Optional[Path]:
    """Generate a bar chart of detections per sample image."""
    if not detection_results:
        return None
    plt.rcParams.update(PLOT_STYLE)
    fig, ax = plt.subplots(figsize=(12, 6))
    names = [r["image"][:20] for r in detection_results]
    counts = [r["num_detections"] for r in detection_results]
    bars = ax.bar(range(len(names)), counts, color="#e94560", edgecolor="#1a1a2e")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Image")
    ax.set_ylabel("Number of Detections")
    ax.set_title("Detections Per Sample Image", fontsize=14, fontweight="bold")
    ax.grid(True, axis="y")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(count), ha="center", va="bottom", fontsize=9)
    path = plots_dir / "detections_per_image.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def export_model(model: Any, model_path: Path, export_dir: Path) -> Dict[str, str]:
    """Export model to multiple formats. Returns dict of format->path."""
    exports: Dict[str, str] = {}

    # Copy original .pt
    dest_pt = export_dir / model_path.name
    shutil.copy2(model_path, dest_pt)
    exports["pytorch"] = str(dest_pt)

    # ONNX export
    try:
        # pyrefly: ignore [missing-import]
        from ultralytics import YOLO
        export_model_obj = YOLO(str(model_path))
        onnx_path = export_model_obj.export(format="onnx")
        if onnx_path and Path(onnx_path).exists():
            dest = export_dir / Path(onnx_path).name
            shutil.move(str(onnx_path), str(dest))
            exports["onnx"] = str(dest)
    except Exception:
        pass

    # TorchScript export
    try:
        # pyrefly: ignore [missing-import]
        from ultralytics import YOLO
        export_model_obj = YOLO(str(model_path))
        ts_path = export_model_obj.export(format="torchscript")
        if ts_path and Path(ts_path).exists():
            dest = export_dir / Path(ts_path).name
            shutil.move(str(ts_path), str(dest))
            exports["torchscript"] = str(dest)
    except Exception:
        pass

    return exports


def generate_evaluation_report(
    output_path: Path,
    model_info: Dict[str, Any],
    val_metrics: Optional[Dict[str, Any]],
    test_metrics: Optional[Dict[str, Any]],
    detection_results: List[Dict[str, Any]],
    exports: Dict[str, str],
    dataset_yaml: str,
    val_image_count: int,
    test_image_count: int,
    config_vars: Dict[str, str],
) -> Path:
    """Generate the full evaluation_report.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# YOLOv8 SKU-110K — Model Evaluation Report",
        "",
        f"**Generated**: {now}",
        "",
        "> This model was trained on the SKU-110K retail product detection dataset.",
        "",
        "---",
        "",
        "## 1. Model Information",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| Model Path | `{model_info.get('model_path', 'N/A')}` |",
        f"| Model Size | {model_info.get('model_size_mb', 'N/A')} MB |",
        f"| YOLO Version | {model_info.get('yolo_version', 'N/A')} |",
        f"| Number of Classes | {model_info.get('num_classes', 'N/A')} |",
        f"| Class Names | {', '.join(model_info.get('class_names', [])) or 'N/A'} |",
        f"| Device | `{model_info.get('device', 'N/A')}` |",
        "",
        "---",
        "",
        "## 2. Dataset Information",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| Dataset | SKU-110K |",
        f"| Dataset YAML | `{dataset_yaml}` |",
        f"| Validation Images | {val_image_count:,} |",
        f"| Test Images | {test_image_count:,} |",
        f"| Number of Classes | 1 (object) |",
        "",
        "---",
        "",
        "## 3. Validation Metrics",
        "",
    ]

    if val_metrics:
        lines.extend([
            "| Metric | Value |",
            "|--------|-------|",
            f"| Precision | {val_metrics.get('precision', 'N/A')} |",
            f"| Recall | {val_metrics.get('recall', 'N/A')} |",
            f"| mAP@0.5 | {val_metrics.get('mAP50', 'N/A')} |",
            f"| mAP@0.5:0.95 | {val_metrics.get('mAP50_95', 'N/A')} |",
            f"| Evaluation Time | {val_metrics.get('evaluation_time_seconds', 'N/A')}s |",
        ])
    else:
        lines.append("*Validation evaluation was not performed or failed.*")

    lines.extend(["", "---", "", "## 4. Test Metrics", ""])

    if test_metrics:
        lines.extend([
            "| Metric | Value |",
            "|--------|-------|",
            f"| Precision | {test_metrics.get('precision', 'N/A')} |",
            f"| Recall | {test_metrics.get('recall', 'N/A')} |",
            f"| mAP@0.5 | {test_metrics.get('mAP50', 'N/A')} |",
            f"| mAP@0.5:0.95 | {test_metrics.get('mAP50_95', 'N/A')} |",
            f"| Evaluation Time | {test_metrics.get('evaluation_time_seconds', 'N/A')}s |",
        ])
    else:
        lines.append("*Test evaluation was not performed — test split configuration unavailable.*")

    lines.extend(["", "---", "", "## 5. Sample Inference Results", ""])

    if detection_results:
        lines.extend(["| Image | Detections | Inference Time |", "|-------|------------|----------------|"])
        for r in detection_results:
            lines.append(f"| {r['image']} | {r['num_detections']} | {r['inference_time_ms']}ms |")
    else:
        lines.append("*No sample inference was performed.*")

    # Sections 6-12
    speed_val = val_metrics.get("inference_speed_ms", "N/A") if val_metrics else "N/A"
    eval_time = val_metrics.get("evaluation_time_seconds", "N/A") if val_metrics else "N/A"

    lines.extend([
        "", "---", "",
        "## 6. Inference Speed", "",
        f"- **Validation inference speed**: {speed_val} ms/image",
        "", "---", "",
        "## 7. Evaluation Time", "",
        f"- **Validation**: {eval_time}s",
    ])
    if test_metrics:
        lines.append(f"- **Test**: {test_metrics.get('evaluation_time_seconds', 'N/A')}s")

    lines.extend([
        "", "---", "",
        "## 8. Device Used", "",
        f"- `{model_info.get('device', 'N/A')}`",
        "", "---", "",
        "## 9. Model File Size", "",
        f"- {model_info.get('model_size_mb', 'N/A')} MB",
        "", "---", "",
        "## 10. Model Path", "",
        f"- `{model_info.get('model_path', 'N/A')}`",
        "", "---", "",
        "## 11. Evaluation Date", "",
        f"- {now}",
        "", "---", "",
        "## 12. Configuration Used", "",
        "| Variable | Value |",
        "|----------|-------|",
    ])
    for k, v in config_vars.items():
        lines.append(f"| {k} | `{v}` |")

    lines.extend([
        "", "---", "",
        "## Exported Models", "",
    ])
    if exports:
        lines.extend(["| Format | Path |", "|--------|------|"])
        for fmt, path in exports.items():
            lines.append(f"| {fmt} | `{path}` |")
    else:
        lines.append("*No exports were generated.*")

    lines.extend([
        "", "---", "",
        "*Report generated automatically by the Consumer Attention Mapping System.*",
        "",
    ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path
