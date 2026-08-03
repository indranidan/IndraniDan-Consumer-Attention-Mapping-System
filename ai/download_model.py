"""
AI Module — Pretrained Model Verification & Downloader
======================================================
Verifies presence of yolov8n.pt, downloads weights automatically if missing,
inspects PyTorch / Ultralytics environment runtime, and displays compute device details.

Usage:
    python ai/download_model.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch
import ultralytics
from ultralytics import YOLO

from ai.config import load_config
from ai.logger import setup_logger
from ai.utils import ensure_directory, get_device, print_banner

logger = setup_logger("download_model")


def verify_or_download_model() -> Path:
    """
    Verify presence of pretrained YOLOv8 model file.
    If missing, download using Ultralytics.

    Returns:
        Path: Path to verified model weights file.
    """
    logger.info("Loading Environment...")
    logger.info("Reading .env...")

    config = load_config()

    models_dir = ensure_directory(config.models_dir)
    model_name = config.model_name

    # Check model path in models_dir or ai root
    model_path = models_dir / model_name
    ai_root_model_path = config.ai_dir / model_name

    target_path = model_path

    if ai_root_model_path.exists() and not model_path.exists():
        target_path = ai_root_model_path

    if target_path.exists():
        logger.info(f"Model file found at: {target_path}")
    else:
        logger.info(f"Model file '{model_name}' not found locally. Downloading automatically...")
        try:
            # YOLO will download to current dir or cache and return model
            temp_model = YOLO(model_name)
            # Ensure model is saved to target_path if downloaded elsewhere
            downloaded_weights = Path(temp_model.ckpt_path) if hasattr(temp_model, "ckpt_path") else Path(model_name)
            if downloaded_weights.exists() and downloaded_weights != target_path:
                import shutil
                shutil.copy(downloaded_weights, target_path)
            elif not target_path.exists() and Path(model_name).exists():
                import shutil
                shutil.move(model_name, target_path)

            logger.info(f"Successfully downloaded model to: {target_path}")
        except Exception as exc:
            raise RuntimeError(f"Failed to download model '{model_name}': {exc}")

    if not target_path.exists():
        raise RuntimeError(f"Model file not present at {target_path}")

    return target_path


def main() -> int:
    """CLI entry point for model verification and environment diagnostics."""
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — Pretrained Model Verification")

    try:
        config = load_config()
        model_path = verify_or_download_model()

        # Gather Environment Specs
        ultralytics_ver = ultralytics.__version__
        torch_ver = torch.__version__
        cuda_available = torch.cuda.is_available()
        device_str = get_device(config.device)

        file_size_bytes = model_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        border = "═" * 60
        thin_border = "─" * 60

        print("\n" + border)
        print("  MODEL & ENVIRONMENT DIAGNOSTICS")
        print(border)
        print(f"  {'Ultralytics Version':<25} : {ultralytics_ver}")
        print(f"  {'PyTorch Version':<25} : {torch_ver}")
        print(f"  {'CUDA Available':<25} : {cuda_available}")
        print(f"  {'Compute Device':<25} : {device_str}")
        print(thin_border)
        print(f"  {'Model Name':<25} : {config.model_name}")
        print(f"  {'Model Path':<25} : {model_path}")
        print(f"  {'Model File Size':<25} : {file_size_mb:.2f} MB")
        print(border + "\n")

        # Load weights check with YOLO
        logger.info("Verifying model weight structure...")
        _ = YOLO(str(model_path))
        logger.info("Model Verified")

        print("✅ Pretrained YOLOv8 model verification PASSED! Model ready for use.\n")
        return 0

    except Exception as err:
        logger.error(f"Model verification failed: {err}")
        print(f"\n❌ Model verification error: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
