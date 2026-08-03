"""
AI Module — Centralized Configuration
======================================
Loads all AI-related settings from the project-root .env file.
Provides a typed, validated AIConfig dataclass used by every other module.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Resolve the project root (parent of ai/)
# ---------------------------------------------------------------------------
_AI_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AI_DIR.parent

# Track whether .env has been loaded
_env_loaded = False


def _ensure_env_loaded() -> None:
    """Load the .env file from the project root (once)."""
    global _env_loaded
    if _env_loaded:
        return

    from dotenv import load_dotenv

    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError(
            f".env file not found at {env_path}\n"
            f"Copy .env.example to .env and fill in your values."
        )

    load_dotenv(dotenv_path=env_path)
    _env_loaded = True


# ---------------------------------------------------------------------------
# Helper: read an env var or raise with a clear message
# ---------------------------------------------------------------------------
def _require_env(key: str) -> str:
    """Return the value of an environment variable, or raise RuntimeError."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"Required environment variable '{key}' is not set in .env"
        )
    return value.strip()


def _optional_env(key: str, default: str = "") -> str:
    """Return the value of an environment variable, or a default."""
    value = os.getenv(key, default)
    return value.strip() if value else default


# ---------------------------------------------------------------------------
# AIConfig dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AIConfig:
    """Immutable configuration for the AI module."""

    # Dataset paths
    coco_dataset_path: Path
    sku110k_dataset_path: Path

    # YOLO settings
    yolo_model_name: str
    yolo_output_path: Path
    device: str
    image_size: int

    # Training specific configurations
    model_name: str
    batch_size: int
    epochs: int
    workers: int
    project_name: str
    run_name: str
    output_directory: Path
    resume_training: bool
    seed: int

    # Evaluation limits (0 = no limit)
    max_eval_samples: int

    # Derived paths
    ai_dir: Path = field(default=_AI_DIR)
    project_root: Path = field(default=_PROJECT_ROOT)
    models_dir: Path = field(default_factory=lambda: _AI_DIR / "models")
    configs_dir: Path = field(default_factory=lambda: _AI_DIR / "configs")


def load_config() -> AIConfig:
    """
    Build an AIConfig from environment variables.

    Returns
    -------
    AIConfig
        Fully validated, immutable configuration object.

    Raises
    ------
    RuntimeError
        If .env is missing or required variables are not set.
    """
    _ensure_env_loaded()

    coco_path = Path(_require_env("COCO_DATASET_PATH"))
    sku110k_path = Path(_require_env("SKU110K_DATASET_PATH"))
    yolo_model = _optional_env("YOLO_MODEL_NAME", "yolov8n.pt")
    yolo_output = Path(
        _optional_env("YOLO_OUTPUT_PATH", str(_AI_DIR / "outputs"))
    )

    # Make relative output paths absolute from project root
    if not yolo_output.is_absolute():
        yolo_output = _PROJECT_ROOT / yolo_output

    device = _optional_env("DEVICE", "cpu")
    image_size = int(_optional_env("IMAGE_SIZE", "640"))
    batch_size = int(_optional_env("BATCH_SIZE", "4"))
    epochs = int(_optional_env("EPOCHS", "50"))
    workers = int(_optional_env("WORKERS", "2"))
    project_name = _optional_env("PROJECT_NAME", "sku110k_training")
    run_name = _optional_env("RUN_NAME", "yolov8n_sku110k_run1")
    output_dir = Path(_optional_env("OUTPUT_DIRECTORY", str(_AI_DIR / "outputs")))
    if not output_dir.is_absolute():
        output_dir = _PROJECT_ROOT / output_dir

    resume_val = _optional_env("RESUME_TRAINING", "false").lower()
    resume_training = resume_val in ("true", "1", "yes")
    seed = int(_optional_env("SEED", "42"))
    max_eval_samples = int(_optional_env("MAX_EVAL_SAMPLES", "100"))

    return AIConfig(
        coco_dataset_path=coco_path,
        sku110k_dataset_path=sku110k_path,
        yolo_model_name=yolo_model,
        yolo_output_path=yolo_output,
        device=device,
        image_size=image_size,
        model_name=yolo_model,
        batch_size=batch_size,
        epochs=epochs,
        workers=workers,
        project_name=project_name,
        run_name=run_name,
        output_directory=output_dir,
        resume_training=resume_training,
        seed=seed,
        max_eval_samples=max_eval_samples,
    )
