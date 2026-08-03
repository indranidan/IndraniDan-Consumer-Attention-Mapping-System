"""
AI Module — YOLOv8 Transfer Learning Pipeline
===============================================
Production-ready training pipeline that fine-tunes a pretrained YOLOv8 model
on the SKU-110K dataset for retail shelf product detection.

Features:
- Loads all configuration from .env (zero hardcoded values)
- Automatic CPU / GPU detection with CUDA fallback
- Transfer learning from yolov8n.pt
- Checkpoint saving (best.pt, last.pt) with resume support
- Post-training visualization and Markdown report generation
- Comprehensive error handling and structured logging

Usage:
    python ai/train.py
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
_AI_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AI_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Project imports (Phase 1 infrastructure)
# ---------------------------------------------------------------------------
from ai.config import load_config, AIConfig
from ai.logger import setup_logger
from ai.utils import get_device, print_banner, timer

from ai.training_utils import (
    copy_checkpoints,
    copy_metrics,
    format_duration,
    generate_training_plots,
    generate_training_report,
    locate_pretrained_model,
    setup_training_directories,
    validate_dataset_yaml,
)


# ---------------------------------------------------------------------------
# Module logger (mutable to allow file handler reconfiguration)
# ---------------------------------------------------------------------------
_logger_ref: list = [setup_logger("train")]


def _get_logger():
    """Return the current module logger."""
    return _logger_ref[0]


def _reconfigure_logger(log_file: Path) -> None:
    """Reconfigure the module logger with a file handler."""
    _logger_ref[0] = setup_logger("train", log_file=log_file)


# ---------------------------------------------------------------------------
# Training Pipeline
# ---------------------------------------------------------------------------
class TrainingPipeline:
    """
    Orchestrates the full YOLOv8 transfer learning workflow.

    Responsibilities:
    1. Load and validate configuration
    2. Detect compute device
    3. Validate dataset YAML
    4. Locate pretrained model
    5. Create output directory structure
    6. Run transfer learning via Ultralytics
    7. Copy checkpoints to canonical location
    8. Generate training plots and report
    """

    def __init__(self) -> None:
        self.config: Optional[AIConfig] = None
        self.device: str = "cpu"
        self.confidence_threshold: float = 0.25
        self.dataset_yaml_path: Optional[Path] = None
        self.model_path: Optional[Path] = None
        self.training_dirs: dict = {}
        self.training_start: Optional[float] = None
        self.training_end: Optional[float] = None

    # ── Step 1: Load Configuration ────────────────────────────
    def load_configuration(self) -> None:
        """Load and validate all configuration from .env."""
        _get_logger().info("═" * 50)
        _get_logger().info("Loading Environment...")
        _get_logger().info("═" * 50)

        self.config = load_config()

        # Read CONFIDENCE_THRESHOLD (not in AIConfig, read directly from env)
        conf_str = os.getenv("CONFIDENCE_THRESHOLD", "0.25").strip()
        try:
            self.confidence_threshold = float(conf_str)
        except ValueError:
            _get_logger().warning(
                f"Invalid CONFIDENCE_THRESHOLD '{conf_str}', using default 0.25"
            )
            self.confidence_threshold = 0.25

        _get_logger().info("Configuration loaded successfully")
        self._print_config_summary()

    def _print_config_summary(self) -> None:
        """Print a formatted summary of training configuration."""
        cfg = self.config
        border = "─" * 55
        print(f"\n{border}")
        print("  TRAINING CONFIGURATION")
        print(border)
        print(f"  {'Model':<25} │ {cfg.model_name}")
        print(f"  {'Image Size':<25} │ {cfg.image_size}")
        print(f"  {'Batch Size':<25} │ {cfg.batch_size}")
        print(f"  {'Epochs':<25} │ {cfg.epochs}")
        print(f"  {'Device (configured)':<25} │ {cfg.device}")
        print(f"  {'Workers':<25} │ {cfg.workers}")
        print(f"  {'Project Name':<25} │ {cfg.project_name}")
        print(f"  {'Run Name':<25} │ {cfg.run_name}")
        print(f"  {'Output Directory':<25} │ {cfg.output_directory}")
        print(f"  {'Resume Training':<25} │ {cfg.resume_training}")
        print(f"  {'Seed':<25} │ {cfg.seed}")
        print(f"  {'Confidence Threshold':<25} │ {self.confidence_threshold}")
        print(f"  {'Dataset':<25} │ {cfg.sku110k_dataset_path}")
        print(f"{border}\n")

    # ── Step 2: Detect Device ─────────────────────────────────
    def detect_device(self) -> None:
        """Detect and select the best available compute device."""
        _get_logger().info("Detecting compute device...")
        self.device = get_device(self.config.device)
        _get_logger().info(f"Selected device: {self.device}")

    # ── Step 3: Validate Dataset ──────────────────────────────
    def validate_dataset(self) -> None:
        """Validate the dataset YAML and verify image directories."""
        _get_logger().info("Loading Dataset Configuration...")
        self.dataset_yaml_path = self.config.configs_dir / "sku110k.yaml"
        validate_dataset_yaml(self.dataset_yaml_path)
        _get_logger().info("Dataset validation complete")

    # ── Step 4: Locate Model ──────────────────────────────────
    def locate_model(self) -> None:
        """Find the pretrained YOLOv8 model file."""
        _get_logger().info("Loading YOLOv8 pretrained model...")
        self.model_path = locate_pretrained_model(
            self.config.ai_dir,
            self.config.model_name,
        )

    # ── Step 5: Setup Directories ─────────────────────────────
    def setup_directories(self) -> None:
        """Create the output directory structure."""
        _get_logger().info("Creating output directory structure...")
        self.training_dirs = setup_training_directories(
            self.config.output_directory,
        )

        # Reconfigure logger with file handler
        log_file = self.training_dirs["logs"] / "training.log"
        _reconfigure_logger(log_file)
        _get_logger().info(f"Log file: {log_file}")

    # ── Step 6: Run Training ──────────────────────────────────
    def run_training(self) -> Path:
        """
        Execute the YOLOv8 transfer learning process.

        Returns
        -------
        Path
            Path to the Ultralytics run directory.

        Raises
        ------
        RuntimeError
            If training fails due to OOM, invalid model, or other errors.
        """
        from ultralytics import YOLO

        _get_logger().info("═" * 50)
        _get_logger().info("Starting YOLOv8 Transfer Learning")
        _get_logger().info("═" * 50)

        # Load model
        try:
            model = YOLO(str(self.model_path))
            _get_logger().info(f"Model loaded: {self.model_path}")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load YOLO model from {self.model_path}: {exc}"
            )

        # Build training arguments
        cfg = self.config
        train_args = {
            "data": str(self.dataset_yaml_path),
            "epochs": cfg.epochs,
            "imgsz": cfg.image_size,
            "batch": cfg.batch_size,
            "device": self.device,
            "workers": cfg.workers,
            "project": str(self.training_dirs["training"]),
            "name": cfg.run_name,
            "seed": cfg.seed,
            "exist_ok": True,
            "pretrained": True,
            "save": True,
            "save_period": 1,
            "conf": self.confidence_threshold,
            "verbose": True,
            "plots": True,
        }

        # Handle resume
        if cfg.resume_training:
            last_pt = self.training_dirs["weights"] / "last.pt"
            if last_pt.exists():
                _get_logger().info(f"Resuming training from: {last_pt}")
                model = YOLO(str(last_pt))
                train_args["resume"] = True
            else:
                _get_logger().warning(
                    f"Resume requested but last.pt not found at {last_pt}. "
                    f"Starting fresh training."
                )

        # Execute training
        self.training_start = time.perf_counter()

        try:
            _get_logger().info("Training started — this may take a while...")
            results = model.train(**train_args)
            self.training_end = time.perf_counter()
            _get_logger().info("Training completed successfully!")

        except torch.cuda.OutOfMemoryError:
            self.training_end = time.perf_counter()
            raise RuntimeError(
                "CUDA Out of Memory! Try reducing BATCH_SIZE or IMAGE_SIZE in .env.\n"
                "Current settings: BATCH_SIZE={}, IMAGE_SIZE={}".format(
                    cfg.batch_size, cfg.image_size
                )
            )
        except RuntimeError as exc:
            self.training_end = time.perf_counter()
            if "out of memory" in str(exc).lower():
                raise RuntimeError(
                    f"Out of Memory error during training.\n"
                    f"Reduce BATCH_SIZE (current: {cfg.batch_size}) or "
                    f"IMAGE_SIZE (current: {cfg.image_size}) in .env.\n"
                    f"Original error: {exc}"
                )
            raise RuntimeError(f"Training failed: {exc}")
        except KeyboardInterrupt:
            self.training_end = time.perf_counter()
            _get_logger().warning("Training interrupted by user (Ctrl+C)")
            _get_logger().info(
                "Training can be resumed by setting RESUME_TRAINING=true in .env"
            )
            # Still try to process whatever was saved

        # Determine the Ultralytics run directory
        run_dir = self.training_dirs["training"] / cfg.run_name
        if not run_dir.exists():
            # Fallback: search for the latest run directory
            training_base = self.training_dirs["training"]
            candidates = sorted(training_base.iterdir(), key=os.path.getmtime)
            run_dirs = [d for d in candidates if d.is_dir() and d.name != "weights"]
            if run_dirs:
                run_dir = run_dirs[-1]
            else:
                _get_logger().warning(f"Could not locate Ultralytics run directory")
                return training_base

        _get_logger().info(f"Ultralytics run directory: {run_dir}")
        return run_dir

    # ── Step 7: Post-Training Processing ──────────────────────
    def post_training(self, run_dir: Path) -> None:
        """
        Copy checkpoints, generate plots, and create the training report.

        Parameters
        ----------
        run_dir : Path
            The Ultralytics training run directory.
        """
        _get_logger().info("═" * 50)
        _get_logger().info("Post-Training Processing")
        _get_logger().info("═" * 50)

        training_time = (
            (self.training_end - self.training_start)
            if self.training_start and self.training_end
            else 0.0
        )

        # Copy checkpoints
        _get_logger().info("Saving checkpoints...")
        best_pt, last_pt = copy_checkpoints(
            run_dir, self.training_dirs["weights"]
        )

        # Copy metrics
        _get_logger().info("Saving metrics...")
        results_csv = copy_metrics(run_dir, self.training_dirs["metrics"])

        # Generate plots
        _get_logger().info("Generating training plots...")
        if results_csv and results_csv.exists():
            with timer("Plot generation", _get_logger()):
                generated_plots = generate_training_plots(
                    results_csv, self.training_dirs["plots"]
                )
            _get_logger().info(f"Generated {len(generated_plots)} plot(s)")
        else:
            _get_logger().warning("Skipping plot generation — results.csv not available")

        # Also copy any Ultralytics-generated plots
        _copy_ultralytics_plots(run_dir, self.training_dirs["plots"])

        # Generate training report
        _get_logger().info("Generating training report...")
        cfg = self.config
        report_path = generate_training_report(
            report_dir=self.training_dirs["reports"],
            training_date=datetime.now(),
            model_name=cfg.model_name,
            dataset_path=str(cfg.sku110k_dataset_path),
            dataset_yaml=str(self.dataset_yaml_path),
            epochs_completed=cfg.epochs,
            epochs_total=cfg.epochs,
            image_size=cfg.image_size,
            batch_size=cfg.batch_size,
            device=self.device,
            training_time_seconds=training_time,
            best_pt_path=best_pt,
            last_pt_path=last_pt,
            results_csv=results_csv,
        )

        # Final summary
        self._print_completion_summary(
            training_time, best_pt, last_pt, report_path
        )

    def _print_completion_summary(
        self,
        training_time: float,
        best_pt: Optional[Path],
        last_pt: Optional[Path],
        report_path: Path,
    ) -> None:
        """Print a formatted training completion summary."""
        border = "═" * 60
        duration = format_duration(training_time)

        print(f"\n{border}")
        print("  ✅ TRAINING COMPLETE")
        print(border)
        print(f"  Training Time     : {duration}")
        if best_pt:
            size_mb = best_pt.stat().st_size / (1024 * 1024)
            print(f"  Best Weights      : {best_pt} ({size_mb:.1f} MB)")
        if last_pt:
            size_mb = last_pt.stat().st_size / (1024 * 1024)
            print(f"  Last Weights      : {last_pt} ({size_mb:.1f} MB)")
        print(f"  Training Report   : {report_path}")
        print(f"  Plots Directory   : {self.training_dirs.get('plots', 'N/A')}")
        print(f"{border}\n")

    # ── Execute Full Pipeline ─────────────────────────────────
    def execute(self) -> int:
        """
        Run the complete training pipeline end-to-end.

        Returns
        -------
        int
            Exit code: 0 for success, 1 for failure.
        """
        try:
            self.load_configuration()
            self.detect_device()
            self.validate_dataset()
            self.locate_model()
            self.setup_directories()
            run_dir = self.run_training()
            self.post_training(run_dir)
            return 0

        except FileNotFoundError as exc:
            _get_logger().error(f"File not found: {exc}")
            print(f"\n❌ {exc}\n")
            return 1

        except ValueError as exc:
            _get_logger().error(f"Validation error: {exc}")
            print(f"\n❌ {exc}\n")
            return 1

        except PermissionError as exc:
            _get_logger().error(f"Permission denied: {exc}")
            print(f"\n❌ Permission error: {exc}\n")
            return 1

        except RuntimeError as exc:
            _get_logger().error(f"Runtime error: {exc}")
            print(f"\n❌ {exc}\n")
            return 1

        except Exception as exc:
            _get_logger().exception(f"Unexpected error during training: {exc}")
            print(f"\n❌ Unexpected error: {exc}\n")
            return 1


# ---------------------------------------------------------------------------
# Helper: Copy Ultralytics-generated plots
# ---------------------------------------------------------------------------
def _copy_ultralytics_plots(run_dir: Path, plots_dir: Path) -> None:
    """
    Copy any plot images generated by Ultralytics during training
    (confusion matrix, PR curves, etc.) to the canonical plots directory.
    """
    import shutil

    if not run_dir.exists():
        return

    plot_extensions = {".png", ".jpg", ".jpeg"}
    copied = 0

    for f in run_dir.iterdir():
        if f.is_file() and f.suffix.lower() in plot_extensions:
            dest = plots_dir / f.name
            if not dest.exists():
                shutil.copy2(f, dest)
                copied += 1

    if copied > 0:
        _get_logger().info(f"Copied {copied} Ultralytics plot(s) to {plots_dir}")


# ---------------------------------------------------------------------------
# Lazy torch import for OOM exception handling
# ---------------------------------------------------------------------------
try:
    import torch
except ImportError:
    # torch will be imported by ultralytics anyway, this is for type safety
    pass


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main() -> int:
    """CLI entry point for the training pipeline."""
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — YOLOv8 Transfer Learning")

    pipeline = TrainingPipeline()
    return pipeline.execute()


if __name__ == "__main__":
    sys.exit(main())
