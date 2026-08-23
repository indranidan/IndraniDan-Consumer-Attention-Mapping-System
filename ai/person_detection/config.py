"""
Person Detection — Configuration
==================================
Module-specific configuration dataclass for person detection.
Reads its own environment variables and delegates to the shared
AI config for common values (DEVICE, IMAGE_SIZE).

Does NOT modify the existing frozen AIConfig dataclass.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is in sys.path
_AI_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AI_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import _ensure_env_loaded, _optional_env, _PROJECT_ROOT as CONFIG_PROJECT_ROOT


# ---------------------------------------------------------------------------
# PersonDetectionConfig dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PersonDetectionConfig:
    """Immutable configuration for the person detection pipeline."""

    # Model path for person detection
    person_model_path: Path

    # Detection settings
    confidence_threshold: float
    image_size: int
    device: str

    # Output control
    save_frames: bool
    output_base: Path

    # Derived paths
    videos_dir: Path
    frames_dir: Path
    reports_dir: Path
    logs_dir: Path


def _resolve_model_path(raw_path: str) -> Path:
    """
    Resolve a model path that may be relative to the project root or CWD.

    Searches across standard canonical model directories:
      1. Exact path (if absolute and exists)
      2. Direct relative path to project root or current working directory
      3. Candidate model folders (ai/models, ai, ai/coco)
      4. Standard COCO model fallbacks if specific model filename is missing

    Parameters
    ----------
    raw_path : str
        Raw path string from environment variable.

    Returns
    -------
    Path
        Resolved absolute path.
    """
    path = Path(raw_path)

    # 1. If absolute and exists, return immediately
    if path.is_absolute() and path.exists():
        return path

    # 2. Check relative to project root
    resolved = CONFIG_PROJECT_ROOT / path
    if resolved.exists():
        return resolved

    # 3. Check relative to CWD
    cwd_resolved = Path.cwd() / path
    if cwd_resolved.exists():
        return cwd_resolved.resolve()

    # 4. Search candidate directories for the specified filename
    filename = path.name
    candidate_dirs = [
        CONFIG_PROJECT_ROOT / "ai" / "models",
        CONFIG_PROJECT_ROOT / "ai",
        CONFIG_PROJECT_ROOT / "ai" / "coco",
        Path.cwd() / "ai" / "models",
        Path.cwd() / "ai",
        Path.cwd() / "ai" / "coco",
    ]

    for cdir in candidate_dirs:
        candidate_file = cdir / filename
        if candidate_file.exists():
            return candidate_file.resolve()

    # 5. Search for alternative COCO-pretrained person detection models
    default_models = ["yolo26n.pt", "yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]
    for def_name in default_models:
        for cdir in candidate_dirs:
            candidate_file = cdir / def_name
            if candidate_file.exists():
                return candidate_file.resolve()

    return resolved


def load_person_detection_config() -> PersonDetectionConfig:
    """
    Build a PersonDetectionConfig from environment variables.

    Priority for model path:
        1. PERSON_MODEL_PATH (explicit person detection model)
        2. BEST_MODEL_PATH   (fallback — validated later for person class)

    Returns
    -------
    PersonDetectionConfig
        Fully constructed configuration object.

    Raises
    ------
    RuntimeError
        If .env is missing or critical values are invalid.
    """
    _ensure_env_loaded()

    # Model path: prefer PERSON_MODEL_PATH, fall back to BEST_MODEL_PATH
    person_model_raw = _optional_env("PERSON_MODEL_PATH", "")
    if person_model_raw:
        person_model_path = _resolve_model_path(person_model_raw)
    else:
        best_model_raw = _optional_env("BEST_MODEL_PATH", "")
        if best_model_raw:
            person_model_path = _resolve_model_path(best_model_raw)
        else:
            raise RuntimeError(
                "Neither PERSON_MODEL_PATH nor BEST_MODEL_PATH is set in .env.\n"
                "Please set PERSON_MODEL_PATH to a COCO-pretrained YOLOv8 model "
                "(e.g., yolov8n.pt) that includes the 'person' class."
            )

    # Detection settings
    confidence_threshold = float(
        _optional_env("PERSON_CONFIDENCE_THRESHOLD", "0.40")
    )
    image_size = int(_optional_env("IMAGE_SIZE", "640"))
    device = _optional_env("DEVICE", "auto")

    # Output control
    save_frames_val = _optional_env("SAVE_FRAMES", "false").lower()
    save_frames = save_frames_val in ("true", "1", "yes")

    # Output directories
    output_base = CONFIG_PROJECT_ROOT / "outputs" / "module3" / "phase1"
    videos_dir = output_base / "videos"
    frames_dir = output_base / "frames"
    reports_dir = output_base / "reports"
    logs_dir = output_base / "logs"

    return PersonDetectionConfig(
        person_model_path=person_model_path,
        confidence_threshold=confidence_threshold,
        image_size=image_size,
        device=device,
        save_frames=save_frames,
        output_base=output_base,
        videos_dir=videos_dir,
        frames_dir=frames_dir,
        reports_dir=reports_dir,
        logs_dir=logs_dir,
    )
