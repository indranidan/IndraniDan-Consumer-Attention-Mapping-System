"""
AI Module — SKU-110K Model Evaluation & Export (CLI Entry Point)
=================================================================
Evaluates the YOLOv8 model trained on SKU-110K and generates a
comprehensive evaluation report with metrics, visualizations,
sample inference results, and optional model exports.

This does NOT train, modify, or move the model.

Usage::

    python ai/sku110k/evaluate.py

Outputs → ai/sku110k/outputs/evaluation/
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_AI_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _AI_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from ai.config import _ensure_env_loaded, _optional_env, _require_env
from ai.logger import setup_logger
from ai.training_utils import format_duration, validate_dataset_yaml
from ai.utils import get_device, print_banner, timer

from ai.sku110k.eval_utils import (
    copy_ultralytics_plots,
    count_dataset_images,
    create_test_yaml,
    export_model,
    generate_confidence_plot,
    generate_detections_per_image_plot,
    generate_evaluation_report,
    get_model_info,
    run_sample_inference,
    run_validation,
    setup_eval_directories,
)


# ---------------------------------------------------------------------------
# Evaluation Pipeline
# ---------------------------------------------------------------------------
class EvaluationPipeline:
    """
    Orchestrates the full YOLOv8 SKU-110K model evaluation workflow.

    Phases:
    1. Load configuration from .env
    2. Validate and load the trained model
    3. Run validation evaluation on SKU-110K val split
    4. Run test evaluation on SKU-110K test split (if available)
    5. Run sample inference with annotated images
    6. Generate detection summary JSON
    7. Generate evaluation report (Markdown)
    8. Generate metrics visualizations
    9. Export model to deployment formats
    """

    def __init__(self) -> None:
        self.model: Any = None
        self.model_path: Optional[Path] = None
        self.model_info: Dict[str, Any] = {}
        self.device: str = "cpu"
        self.image_size: int = 640
        self.confidence_threshold: float = 0.25
        self.sample_count: int = 10
        self.dataset_yaml_path: Optional[Path] = None
        self.eval_output_path: Optional[Path] = None
        self.eval_dirs: Dict[str, Path] = {}
        self.val_metrics: Optional[Dict[str, Any]] = None
        self.test_metrics: Optional[Dict[str, Any]] = None
        self.detection_results: List[Dict[str, Any]] = []
        self.exports: Dict[str, str] = {}
        self.config_vars: Dict[str, str] = {}
        self.val_run_dir: Optional[Path] = None
        self.test_run_dir: Optional[Path] = None

    # ── Phase 3.9 & 3.1: Configuration & Model Validation ────
    def load_configuration(self, log: Any) -> None:
        """Load all configuration from .env and validate the model."""
        log.info("Loading environment...")
        _ensure_env_loaded()

        # Read all config from .env
        best_model = _require_env("BEST_MODEL_PATH")
        model_path = Path(best_model)
        if not model_path.is_absolute():
            model_path = _PROJECT_ROOT / model_path
        self.model_path = model_path

        self.dataset_yaml_path = Path(
            _optional_env("SKU110K_YAML_PATH", "ai/configs/sku110k.yaml")
        )
        if not self.dataset_yaml_path.is_absolute():
            self.dataset_yaml_path = _PROJECT_ROOT / self.dataset_yaml_path

        eval_out = _optional_env(
            "EVALUATION_OUTPUT_PATH", "ai/sku110k/outputs/evaluation"
        )
        self.eval_output_path = Path(eval_out)
        if not self.eval_output_path.is_absolute():
            self.eval_output_path = _PROJECT_ROOT / self.eval_output_path

        self.device = _optional_env("DEVICE", "cpu")
        self.image_size = int(_optional_env("IMAGE_SIZE", "640"))
        self.confidence_threshold = float(
            _optional_env("CONFIDENCE_THRESHOLD", "0.25")
        )
        self.sample_count = int(_optional_env("SAMPLE_COUNT", "10"))

        # Store for report
        self.config_vars = {
            "BEST_MODEL_PATH": str(self.model_path),
            "SKU110K_YAML_PATH": str(self.dataset_yaml_path),
            "EVALUATION_OUTPUT_PATH": str(self.eval_output_path),
            "DEVICE": self.device,
            "IMAGE_SIZE": str(self.image_size),
            "CONFIDENCE_THRESHOLD": str(self.confidence_threshold),
            "SAMPLE_COUNT": str(self.sample_count),
        }

        log.info("Configuration loaded successfully")
        self._print_config(log)

    def _print_config(self, log: Any) -> None:
        border = "─" * 55
        print(f"\n{border}")
        print("  EVALUATION CONFIGURATION")
        print(border)
        for k, v in self.config_vars.items():
            print(f"  {k:<30} │ {v}")
        print(f"{border}\n")

    def validate_model(self, log: Any) -> None:
        """Validate and load the trained YOLOv8 model (Phase 3.1)."""
        log.info(f"Reading model path: {self.model_path}")

        # Check file exists
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at: {self.model_path}\n"
                f"Check BEST_MODEL_PATH in .env.\n"
                f"The training may still be in progress."
            )

        # Check readable
        if not os.access(self.model_path, os.R_OK):
            raise PermissionError(
                f"Model file is not readable: {self.model_path}\n"
                f"Check file permissions."
            )

        log.info("Model found")
        size_mb = self.model_path.stat().st_size / (1024 * 1024)
        log.info(f"  File size: {size_mb:.2f} MB")

        # Load model
        log.info("Loading YOLOv8...")
        try:
            # pyrefly: ignore [missing-import]
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
        except ImportError:
            raise RuntimeError(
                "Ultralytics is not installed. "
                "Run: pip install -r ai/requirements.txt"
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load model from {self.model_path}: {exc}\n"
                f"The model file may be corrupted or incompatible."
            )

        log.info("Model loaded successfully")

        # Detect device
        self.device = get_device(self.device)
        self.config_vars["DEVICE"] = self.device

        # Display model info
        self.model_info = get_model_info(self.model, self.model_path, self.device)
        border = "─" * 55
        print(f"\n{border}")
        print("  MODEL INFORMATION")
        print(border)
        print(f"  {'Model Path':<25} │ {self.model_info['model_path']}")
        print(f"  {'Model Size':<25} │ {self.model_info['model_size_mb']} MB")
        print(f"  {'YOLO Version':<25} │ {self.model_info['yolo_version']}")
        print(f"  {'Number of Classes':<25} │ {self.model_info['num_classes']}")
        print(f"  {'Class Names':<25} │ {self.model_info['class_names']}")
        print(f"  {'Device':<25} │ {self.model_info['device']}")
        print(f"{border}\n")

    # ── Phase 3.2: Validation Evaluation ──────────────────────
    def run_validation_eval(self, log: Any) -> None:
        """Evaluate model on SKU-110K validation split."""
        log.info("Loading SKU-110K configuration...")
        validate_dataset_yaml(self.dataset_yaml_path)
        log.info("Dataset configuration validated")

        log.info("Running validation evaluation...")
        with timer("Validation evaluation", log):
            self.val_metrics, self.val_run_dir = run_validation(
                model=self.model,
                data_yaml=str(self.dataset_yaml_path),
                imgsz=self.image_size,
                device=self.device,
                project=str(self.eval_dirs["root"]),
                name="val_results",
                conf=self.confidence_threshold,
            )

        if self.val_metrics:
            log.info("Validation evaluation complete")
            self._print_metrics("VALIDATION RESULTS", self.val_metrics, log)
        else:
            log.warning("Validation evaluation failed or returned no metrics")

    def _print_metrics(
        self, title: str, metrics: Dict[str, Any], log: Any
    ) -> None:
        border = "─" * 55
        print(f"\n{border}")
        print(f"  {title}")
        print(border)
        for key in ["precision", "recall", "mAP50", "mAP50_95"]:
            val = metrics.get(key, "N/A")
            label = key.replace("_", "@0.5:0.") if key == "mAP50_95" else key
            if key == "mAP50_95":
                label = "mAP@0.5:0.95"
            elif key == "mAP50":
                label = "mAP@0.5"
            print(f"  {label:<25} │ {val}")
        eval_t = metrics.get("evaluation_time_seconds", "N/A")
        speed = metrics.get("inference_speed_ms", "N/A")
        print(f"  {'Evaluation Time':<25} │ {eval_t}s")
        print(f"  {'Inference Speed':<25} │ {speed} ms/image")
        print(f"{border}\n")

    # ── Phase 3.3: Test Evaluation ────────────────────────────
    def run_test_eval(self, log: Any) -> None:
        """Evaluate model on SKU-110K test split if available."""
        log.info("Running test evaluation...")

        test_yaml = create_test_yaml(
            self.dataset_yaml_path, "test", self.eval_dirs["root"]
        )
        if test_yaml is None:
            log.warning(
                "Test evaluation skipped — test split configuration "
                "unavailable or test directory is empty."
            )
            return

        with timer("Test evaluation", log):
            self.test_metrics, self.test_run_dir = run_validation(
                model=self.model,
                data_yaml=str(test_yaml),
                imgsz=self.image_size,
                device=self.device,
                project=str(self.eval_dirs["root"]),
                name="test_results",
                conf=self.confidence_threshold,
            )

        if self.test_metrics:
            log.info("Test evaluation complete")
            self._print_metrics("TEST RESULTS", self.test_metrics, log)
        else:
            log.warning("Test evaluation failed or returned no metrics")

    # ── Phase 3.4 & 3.5: Sample Inference & Detection Summary ─
    def run_inference(self, log: Any) -> None:
        """Run sample inference and generate detection summary."""
        log.info(f"Running sample inference ({self.sample_count} images)...")

        with timer("Sample inference", log):
            self.detection_results = run_sample_inference(
                model=self.model,
                yaml_path=self.dataset_yaml_path,
                sample_count=self.sample_count,
                imgsz=self.image_size,
                device=self.device,
                conf=self.confidence_threshold,
                output_dir=self.eval_dirs["inference"],
            )

        log.info(f"Processed {len(self.detection_results)} sample images")

        # Log per-image summary
        for r in self.detection_results:
            log.info(
                f"  {r['image']}: {r['num_detections']} detections, "
                f"{r['inference_time_ms']}ms"
            )

        # Save detection_results.json (Phase 3.5)
        det_path = self.eval_dirs["root"] / "detection_results.json"
        try:
            with open(det_path, "w", encoding="utf-8") as f:
                json.dump(self.detection_results, f, indent=2, ensure_ascii=False)
            log.info(f"Detection results saved: {det_path}")
        except (PermissionError, OSError) as exc:
            log.error(f"Failed to save detection results: {exc}")

    # ── Phase 3.7: Metrics Visualization ──────────────────────
    def generate_plots(self, log: Any) -> None:
        """Generate evaluation visualizations."""
        log.info("Generating plots...")
        plots_dir = self.eval_dirs["plots"]
        plot_count = 0

        # Copy Ultralytics-generated plots from validation
        copied = copy_ultralytics_plots(self.val_run_dir, plots_dir)
        plot_count += copied
        if copied:
            log.info(f"Copied {copied} validation plot(s)")

        # Copy Ultralytics-generated plots from test
        copied = copy_ultralytics_plots(self.test_run_dir, plots_dir)
        plot_count += copied
        if copied:
            log.info(f"Copied {copied} test plot(s)")

        # Generate custom plots
        conf_plot = generate_confidence_plot(self.detection_results, plots_dir)
        if conf_plot:
            plot_count += 1
            log.info(f"Plot saved: {conf_plot}")

        det_plot = generate_detections_per_image_plot(
            self.detection_results, plots_dir
        )
        if det_plot:
            plot_count += 1
            log.info(f"Plot saved: {det_plot}")

        log.info(f"Generated {plot_count} total plot(s)")

    # ── Phase 3.8: Model Export ───────────────────────────────
    def export_models(self, log: Any) -> None:
        """Export model to deployment formats."""
        log.info("Exporting model...")

        try:
            self.exports = export_model(
                self.model, self.model_path, self.eval_dirs["exported_models"]
            )
            for fmt, path in self.exports.items():
                log.info(f"  Exported {fmt}: {path}")
        except Exception as exc:
            log.warning(f"Model export failed: {exc}")

    # ── Phase 3.6: Evaluation Report ──────────────────────────
    def generate_report(self, log: Any) -> None:
        """Generate the full evaluation report and metrics JSON."""
        log.info("Generating report...")

        # evaluation_metrics.json
        metrics_data = {
            "model_info": self.model_info,
            "validation_metrics": self.val_metrics,
            "test_metrics": self.test_metrics,
            "device": self.device,
            "image_size": self.image_size,
            "confidence_threshold": self.confidence_threshold,
        }
        metrics_path = self.eval_dirs["root"] / "evaluation_metrics.json"
        try:
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            log.info(f"Metrics JSON saved: {metrics_path}")
        except (PermissionError, OSError) as exc:
            log.error(f"Failed to save metrics JSON: {exc}")

        # evaluation_report.md
        val_count = count_dataset_images(self.dataset_yaml_path, "val")
        test_count = count_dataset_images(self.dataset_yaml_path, "test")

        report_path = self.eval_dirs["root"] / "evaluation_report.md"
        generate_evaluation_report(
            output_path=report_path,
            model_info=self.model_info,
            val_metrics=self.val_metrics,
            test_metrics=self.test_metrics,
            detection_results=self.detection_results,
            exports=self.exports,
            dataset_yaml=str(self.dataset_yaml_path),
            val_image_count=val_count,
            test_image_count=test_count,
            config_vars=self.config_vars,
        )
        log.info(f"Evaluation report saved: {report_path}")

    # ── Execute Full Pipeline ─────────────────────────────────
    def execute(self) -> int:
        """Run the complete evaluation pipeline. Returns 0 on success."""
        # Setup logger with file handler
        log_file = None
        try:
            _ensure_env_loaded()
            eval_out = _optional_env(
                "EVALUATION_OUTPUT_PATH", "ai/sku110k/outputs/evaluation"
            )
            eval_path = Path(eval_out)
            if not eval_path.is_absolute():
                eval_path = _PROJECT_ROOT / eval_path
            # Clean and recreate evaluation output directories
            self.eval_dirs = setup_eval_directories(eval_path, clean_existing=True)
            log_file = eval_path / "evaluation.log"
        except Exception:
            pass

        log = setup_logger("sku110k_evaluation", log_file=log_file)

        try:
            # Phase 3.9 & 3.1
            self.load_configuration(log)
            self.validate_model(log)

            # Ensure evaluation directories are ready
            if not self.eval_dirs:
                self.eval_dirs = setup_eval_directories(self.eval_output_path)

            # Phase 3.2
            self.run_validation_eval(log)

            # Phase 3.3
            self.run_test_eval(log)

            # Phase 3.4 & 3.5
            self.run_inference(log)

            # Phase 3.7
            self.generate_plots(log)

            # Phase 3.8
            self.export_models(log)

            # Phase 3.6
            self.generate_report(log)

            # Done
            log.info("Evaluation completed successfully.")
            self._print_completion(log)
            return 0

        except FileNotFoundError as exc:
            log.error(f"File not found: {exc}")
            print(f"\n❌ {exc}\n")
            return 1

        except PermissionError as exc:
            log.error(f"Permission denied: {exc}")
            print(f"\n❌ Permission error: {exc}\n")
            return 1

        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                log.error(
                    f"Out of memory! Reduce IMAGE_SIZE in .env "
                    f"(current: {self.image_size}). Error: {exc}"
                )
            else:
                log.error(f"Runtime error: {exc}")
            print(f"\n❌ {exc}\n")
            return 1

        except ValueError as exc:
            log.error(f"Validation error: {exc}")
            print(f"\n❌ {exc}\n")
            return 1

        except KeyboardInterrupt:
            log.warning("Evaluation interrupted by user (Ctrl+C)")
            print("\n⚠ Evaluation interrupted.\n")
            return 1

        except Exception as exc:
            log.exception(f"Unexpected error: {exc}")
            print(f"\n❌ Unexpected error: {exc}\n")
            return 1

    def _print_completion(self, log: Any) -> None:
        border = "═" * 60
        print(f"\n{border}")
        print("  ✅ EVALUATION COMPLETE")
        print(border)
        print(f"  Output Directory  : {self.eval_output_path}")
        if self.val_metrics:
            p = self.val_metrics.get("precision", "N/A")
            m = self.val_metrics.get("mAP50", "N/A")
            print(f"  Val Precision     : {p}")
            print(f"  Val mAP@0.5       : {m}")
        if self.test_metrics:
            p = self.test_metrics.get("precision", "N/A")
            m = self.test_metrics.get("mAP50", "N/A")
            print(f"  Test Precision    : {p}")
            print(f"  Test mAP@0.5      : {m}")
        print(f"  Sample Images     : {len(self.detection_results)}")
        print(f"  Exports           : {list(self.exports.keys())}")
        print(f"{border}\n")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main() -> int:
    """CLI entry point for the SKU-110K evaluation pipeline."""
    print_banner(
        "CONSUMER ATTENTION MAPPING SYSTEM — "
        "SKU-110K Model Evaluation & Export"
    )
    pipeline = EvaluationPipeline()
    return pipeline.execute()


if __name__ == "__main__":
    sys.exit(main())
