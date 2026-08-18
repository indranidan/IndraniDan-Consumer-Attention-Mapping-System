"""
AI Module — Training Utility Functions
========================================
Reusable helper functions for the YOLOv8 transfer learning pipeline:
- Dataset YAML validation
- Pretrained model locator
- Training output directory setup
- Checkpoint management
- Post-training visualization (loss, precision, recall, mAP curves)
- Markdown training report generator
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from ai.logger import setup_logger

matplotlib.use("Agg")  # Non-interactive backend for headless environments

logger = setup_logger("training_utils")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_REQUIRED_YAML_KEYS: List[str] = ["path", "train", "val", "nc", "names"]

_TRAINING_SUBDIRS: List[str] = [
    "weights",
    "metrics",
    "plots",
    "logs",
    "reports",
]


# ---------------------------------------------------------------------------
# Dataset YAML Validation
# ---------------------------------------------------------------------------
def validate_dataset_yaml(yaml_path: Path) -> Dict[str, Any]:
    """
    Load and validate a YOLO dataset YAML configuration file.

    Parameters
    ----------
    yaml_path : Path
        Absolute path to the dataset YAML file (e.g. ``ai/configs/sku110k.yaml``).

    Returns
    -------
    Dict[str, Any]
        Parsed YAML data dictionary.

    Raises
    ------
    FileNotFoundError
        If the YAML file does not exist.
    ValueError
        If required keys are missing or dataset directories are not found.
    """
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Dataset YAML not found at: {yaml_path}\n"
            f"Run 'python ai/generate_yaml.py' to generate it."
        )

    with open(yaml_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not data:
        raise ValueError(f"Dataset YAML is empty: {yaml_path}")

    # Check required keys
    missing_keys = [k for k in _REQUIRED_YAML_KEYS if k not in data]
    if missing_keys:
        raise ValueError(
            f"Dataset YAML missing required keys: {missing_keys}\n"
            f"File: {yaml_path}"
        )

    # Validate dataset root exists
    dataset_root = Path(data["path"])
    if not dataset_root.exists():
        raise FileNotFoundError(
            f"Dataset root directory not found: {dataset_root}\n"
            f"Check SKU110K_DATASET_PATH in .env"
        )

    # Validate train and val image directories
    for split_key in ("train", "val"):
        split_dir = dataset_root / data[split_key]
        if not split_dir.exists():
            raise FileNotFoundError(
                f"Dataset {split_key} directory not found: {split_dir}"
            )

        image_count = len(list(split_dir.glob("*")))
        if image_count == 0:
            raise ValueError(
                f"Dataset {split_key} directory is empty: {split_dir}"
            )
        logger.info(f"Dataset {split_key} split: {image_count:,} images found")

    logger.info(f"Dataset YAML validated: {yaml_path}")
    return data


# ---------------------------------------------------------------------------
# Pretrained Model Locator
# ---------------------------------------------------------------------------
def locate_pretrained_model(ai_dir: Path, model_name: str) -> Path:
    """
    Locate the pretrained YOLO model file.

    Searches in order:
    1. ``ai/<model_name>`` (Phase 1 default location)
    2. ``ai/models/<model_name>``

    Parameters
    ----------
    ai_dir : Path
        Absolute path to the ``ai/`` directory.
    model_name : str
        Model filename (e.g. ``yolov8n.pt``).

    Returns
    -------
    Path
        Absolute path to the located model file.

    Raises
    ------
    FileNotFoundError
        If the model is not found in any expected location.
    """
    search_paths = [
        ai_dir / model_name,
        ai_dir / "models" / model_name,
    ]

    for candidate in search_paths:
        if candidate.exists():
            size_mb = candidate.stat().st_size / (1024 * 1024)
            logger.info(f"Pretrained model found: {candidate} ({size_mb:.1f} MB)")
            return candidate

    searched = "\n  ".join(str(p) for p in search_paths)
    raise FileNotFoundError(
        f"Pretrained model '{model_name}' not found.\n"
        f"Searched:\n  {searched}\n"
        f"Run 'python ai/download_model.py' to download it."
    )


# ---------------------------------------------------------------------------
# Training Output Directory Setup
# ---------------------------------------------------------------------------
def setup_training_directories(output_dir: Path) -> Dict[str, Path]:
    """
    Create the structured output directory tree for a training run.

    Creates::

        outputs/training/{weights,metrics,plots,logs,reports}

    Parameters
    ----------
    output_dir : Path
        Base output directory (e.g. ``ai/outputs``).

    Returns
    -------
    Dict[str, Path]
        Mapping of subdirectory names to their absolute paths.
    """
    training_base = output_dir / "training"
    dirs: Dict[str, Path] = {"training": training_base}

    for subdir in _TRAINING_SUBDIRS:
        dir_path = training_base / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        dirs[subdir] = dir_path

    logger.info(f"Training output directories ready: {training_base}")
    return dirs


# ---------------------------------------------------------------------------
# Checkpoint Management
# ---------------------------------------------------------------------------
def copy_checkpoints(
    yolo_run_dir: Path,
    target_weights_dir: Path,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Copy best.pt and last.pt from the Ultralytics run directory to
    the canonical weights location.

    Parameters
    ----------
    yolo_run_dir : Path
        Path to the Ultralytics training run directory (contains ``weights/``).
    target_weights_dir : Path
        Destination directory (``outputs/training/weights/``).

    Returns
    -------
    Tuple[Optional[Path], Optional[Path]]
        Paths to the copied (best_pt, last_pt), or None if not found.
    """
    target_weights_dir.mkdir(parents=True, exist_ok=True)
    results: List[Optional[Path]] = []

    for ckpt_name in ("best.pt", "last.pt"):
        source = yolo_run_dir / "weights" / ckpt_name
        if source.exists():
            dest = target_weights_dir / ckpt_name
            shutil.copy2(source, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info(f"Checkpoint saved: {dest} ({size_mb:.1f} MB)")
            results.append(dest)
        else:
            logger.warning(f"Checkpoint not found in run directory: {source}")
            results.append(None)

    return results[0], results[1]


# ---------------------------------------------------------------------------
# Copy Metrics
# ---------------------------------------------------------------------------
def copy_metrics(yolo_run_dir: Path, target_metrics_dir: Path) -> Optional[Path]:
    """
    Copy the ``results.csv`` metrics file from the Ultralytics run directory.

    Parameters
    ----------
    yolo_run_dir : Path
        Path to the Ultralytics training run directory.
    target_metrics_dir : Path
        Destination directory (``outputs/training/metrics/``).

    Returns
    -------
    Optional[Path]
        Path to the copied CSV, or None if not found.
    """
    target_metrics_dir.mkdir(parents=True, exist_ok=True)
    source = yolo_run_dir / "results.csv"

    if source.exists():
        dest = target_metrics_dir / "results.csv"
        shutil.copy2(source, dest)
        logger.info(f"Metrics saved: {dest}")
        return dest

    logger.warning(f"results.csv not found in: {yolo_run_dir}")
    return None


# ---------------------------------------------------------------------------
# Post-Training Visualization
# ---------------------------------------------------------------------------
def generate_training_plots(results_csv: Path, plots_dir: Path) -> List[Path]:
    """
    Parse the Ultralytics ``results.csv`` and generate publication-quality
    training curves.

    Generates:
    - ``loss_curve.png``       — box, cls, dfl losses
    - ``precision_curve.png``
    - ``recall_curve.png``
    - ``map_curve.png``        — mAP50 and mAP50-95
    - ``training_summary.png`` — combined 2×2 overview

    Parameters
    ----------
    results_csv : Path
        Path to the ``results.csv`` file.
    plots_dir : Path
        Directory to save generated plots.

    Returns
    -------
    List[Path]
        Paths to all generated plot files.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []

    if not results_csv.exists():
        logger.warning(f"results.csv not found at {results_csv}, skipping plots.")
        return generated

    # Read CSV — Ultralytics adds leading spaces to column names
    df = pd.read_csv(results_csv)
    df.columns = df.columns.str.strip()

    epochs = df.index + 1  # 1-indexed

    # --- Style configuration ---
    plt.rcParams.update({
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
    })

    # ── 1. Loss Curve ─────────────────────────────────────────
    loss_cols = _find_columns(df, ["train/box_loss", "train/cls_loss", "train/dfl_loss"])
    if loss_cols:
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ["#e94560", "#0f3460", "#53d8fb"]
        for col, color in zip(loss_cols, colors):
            ax.plot(epochs, df[col], label=col, linewidth=2, color=color)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.set_title("Training Loss Curves", fontsize=14, fontweight="bold")
        ax.legend(framealpha=0.8)
        ax.grid(True)
        path = plots_dir / "loss_curve.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        generated.append(path)
        logger.info(f"Plot saved: {path}")

    # ── 2. Precision Curve ────────────────────────────────────
    prec_cols = _find_columns(df, ["metrics/precision(B)"])
    if prec_cols:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(epochs, df[prec_cols[0]], linewidth=2, color="#53d8fb", marker="o", markersize=3)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Precision")
        ax.set_title("Precision Curve", fontsize=14, fontweight="bold")
        ax.grid(True)
        ax.set_ylim(0, 1.05)
        path = plots_dir / "precision_curve.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        generated.append(path)
        logger.info(f"Plot saved: {path}")

    # ── 3. Recall Curve ───────────────────────────────────────
    recall_cols = _find_columns(df, ["metrics/recall(B)"])
    if recall_cols:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(epochs, df[recall_cols[0]], linewidth=2, color="#e94560", marker="o", markersize=3)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Recall")
        ax.set_title("Recall Curve", fontsize=14, fontweight="bold")
        ax.grid(True)
        ax.set_ylim(0, 1.05)
        path = plots_dir / "recall_curve.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        generated.append(path)
        logger.info(f"Plot saved: {path}")

    # ── 4. mAP Curve ─────────────────────────────────────────
    map_cols = _find_columns(df, ["metrics/mAP50(B)", "metrics/mAP50-95(B)"])
    if map_cols:
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ["#53d8fb", "#e94560"]
        labels = ["mAP50", "mAP50-95"]
        for col, color, label in zip(map_cols, colors, labels):
            ax.plot(epochs, df[col], linewidth=2, color=color, label=label)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("mAP")
        ax.set_title("Mean Average Precision Curves", fontsize=14, fontweight="bold")
        ax.legend(framealpha=0.8)
        ax.grid(True)
        ax.set_ylim(0, 1.05)
        path = plots_dir / "map_curve.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        generated.append(path)
        logger.info(f"Plot saved: {path}")

    # ── 5. Training Summary (2×2) ─────────────────────────────
    summary_path = _generate_summary_plot(df, epochs, plots_dir)
    if summary_path:
        generated.append(summary_path)

    return generated


def _find_columns(df: pd.DataFrame, candidates: List[str]) -> List[str]:
    """Return the subset of candidate column names that exist in the DataFrame."""
    return [c for c in candidates if c in df.columns]


def _generate_summary_plot(
    df: pd.DataFrame,
    epochs: Any,
    plots_dir: Path,
) -> Optional[Path]:
    """Generate a combined 2×2 training summary plot."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "YOLOv8 SKU-110K Training Summary",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    plot_configs = [
        {
            "ax": axes[0, 0],
            "cols": ["train/box_loss", "train/cls_loss", "train/dfl_loss"],
            "title": "Training Loss",
            "ylabel": "Loss",
            "colors": ["#e94560", "#0f3460", "#53d8fb"],
        },
        {
            "ax": axes[0, 1],
            "cols": ["metrics/precision(B)"],
            "title": "Precision",
            "ylabel": "Precision",
            "colors": ["#53d8fb"],
        },
        {
            "ax": axes[1, 0],
            "cols": ["metrics/recall(B)"],
            "title": "Recall",
            "ylabel": "Recall",
            "colors": ["#e94560"],
        },
        {
            "ax": axes[1, 1],
            "cols": ["metrics/mAP50(B)", "metrics/mAP50-95(B)"],
            "title": "mAP",
            "ylabel": "mAP",
            "colors": ["#53d8fb", "#e94560"],
        },
    ]

    has_data = False
    for cfg in plot_configs:
        ax = cfg["ax"]
        available = _find_columns(df, cfg["cols"])
        if available:
            has_data = True
            labels_map = {
                "metrics/mAP50(B)": "mAP50",
                "metrics/mAP50-95(B)": "mAP50-95",
            }
            for col, color in zip(available, cfg["colors"]):
                label = labels_map.get(col, col)
                ax.plot(epochs, df[col], linewidth=1.8, color=color, label=label)
            if len(available) > 1:
                ax.legend(fontsize=9, framealpha=0.8)
        ax.set_title(cfg["title"], fontsize=12, fontweight="bold")
        ax.set_xlabel("Epoch", fontsize=10)
        ax.set_ylabel(cfg["ylabel"], fontsize=10)
        ax.grid(True)

    if not has_data:
        plt.close(fig)
        return None

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = plots_dir / "training_summary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Plot saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Training Report Generation
# ---------------------------------------------------------------------------
def generate_training_report(
    report_dir: Path,
    *,
    training_date: datetime,
    model_name: str,
    dataset_path: str,
    dataset_yaml: str,
    epochs_completed: int,
    epochs_total: int,
    image_size: int,
    batch_size: int,
    device: str,
    training_time_seconds: float,
    best_pt_path: Optional[Path],
    last_pt_path: Optional[Path],
    results_csv: Optional[Path],
) -> Path:
    """
    Generate a Markdown training report summarizing the completed run.

    Parameters
    ----------
    report_dir : Path
        Directory to write ``training_report.md``.
    training_date : datetime
        Timestamp when training started.
    model_name : str
        Base model name (e.g. ``yolov8n.pt``).
    dataset_path : str
        SKU-110K dataset root path.
    dataset_yaml : str
        Path to the dataset YAML used.
    epochs_completed : int
        Number of epochs that ran.
    epochs_total : int
        Total epochs configured.
    image_size : int
        Input image resolution.
    batch_size : int
        Batch size used.
    device : str
        Compute device (``cpu`` / ``cuda:0``).
    training_time_seconds : float
        Total wall-clock training time.
    best_pt_path : Optional[Path]
        Path to best.pt checkpoint.
    last_pt_path : Optional[Path]
        Path to last.pt checkpoint.
    results_csv : Optional[Path]
        Path to results.csv for extracting final metrics.

    Returns
    -------
    Path
        Absolute path to the generated report file.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "training_report.md"

    # Extract final metrics from results.csv
    precision, recall, map50, map50_95 = _extract_final_metrics(results_csv)

    duration = format_duration(training_time_seconds)

    lines = [
        "# YOLOv8 SKU-110K Transfer Learning — Training Report",
        "",
        f"**Generated**: {training_date.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Training Configuration",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Training Date | {training_date.strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| Model Used | `{model_name}` |",
        f"| Dataset | `{dataset_path}` |",
        f"| Dataset YAML | `{dataset_yaml}` |",
        f"| Epochs (completed / total) | {epochs_completed} / {epochs_total} |",
        f"| Image Size | {image_size} |",
        f"| Batch Size | {batch_size} |",
        f"| Device | `{device}` |",
        f"| Training Time | {duration} |",
        "",
        "---",
        "",
        "## Final Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Precision | {precision} |",
        f"| Recall | {recall} |",
        f"| mAP50 | {map50} |",
        f"| mAP50-95 | {map50_95} |",
        "",
        "---",
        "",
        "## Checkpoints",
        "",
        "| Checkpoint | Path |",
        "|------------|------|",
        f"| best.pt | `{best_pt_path or 'Not available'}` |",
        f"| last.pt | `{last_pt_path or 'Not available'}` |",
        "",
        "---",
        "",
        "*Report generated automatically by the Consumer Attention Mapping System.*",
        "",
    ]

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    logger.info(f"Training report saved: {report_path}")
    return report_path


def _extract_final_metrics(
    results_csv: Optional[Path],
) -> Tuple[str, str, str, str]:
    """
    Extract the last-epoch metrics from results.csv.

    Returns
    -------
    Tuple[str, str, str, str]
        (precision, recall, mAP50, mAP50-95) as formatted strings.
    """
    default = ("N/A", "N/A", "N/A", "N/A")

    if results_csv is None or not results_csv.exists():
        return default

    try:
        df = pd.read_csv(results_csv)
        df.columns = df.columns.str.strip()
        last = df.iloc[-1]

        precision = f"{last.get('metrics/precision(B)', 'N/A'):.4f}" \
            if "metrics/precision(B)" in df.columns else "N/A"
        recall = f"{last.get('metrics/recall(B)', 'N/A'):.4f}" \
            if "metrics/recall(B)" in df.columns else "N/A"
        map50 = f"{last.get('metrics/mAP50(B)', 'N/A'):.4f}" \
            if "metrics/mAP50(B)" in df.columns else "N/A"
        map50_95 = f"{last.get('metrics/mAP50-95(B)', 'N/A'):.4f}" \
            if "metrics/mAP50-95(B)" in df.columns else "N/A"

        return precision, recall, map50, map50_95

    except Exception as exc:
        logger.warning(f"Could not extract metrics from {results_csv}: {exc}")
        return default


# ---------------------------------------------------------------------------
# Time Formatting
# ---------------------------------------------------------------------------
def format_duration(seconds: float) -> str:
    """
    Convert seconds to a human-readable ``HH:MM:SS`` string.

    Parameters
    ----------
    seconds : float
        Duration in seconds.

    Returns
    -------
    str
        Formatted duration string.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
