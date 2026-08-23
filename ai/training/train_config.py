"""
AI Module — Training Configuration Inspector (CLI)
===================================================
Loads, validates, and prints the YOLOv8 SKU-110K training configuration
dynamically read from project .env. Ensures zero hardcoded configurations.

Usage:
    python ai/train_config.py
"""

import sys
from dataclasses import asdict
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import AIConfig, load_config
from ai.logger import setup_logger
from ai.utils import print_banner, setup_output_directories

logger = setup_logger("train_config")


def get_training_config() -> AIConfig:
    """
    Load and return validated training configuration object.

    Returns:
        AIConfig: Loaded immutable configuration.
    """
    logger.info("Loading Environment...")
    logger.info("Reading .env...")

    config = load_config()

    logger.info("Configuration Loaded")

    # Initialize output subdirectories
    output_dirs = setup_output_directories(config.output_directory)
    logger.info(f"Output Directories Created at: {config.output_directory}")

    return config


def main() -> int:
    """CLI entry point to inspect training configuration."""
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — Training Configuration")

    try:
        config = get_training_config()

        border = "═" * 65
        thin_border = "─" * 65

        print(border)
        print("  YOLOV8 SKU-110K TRAINING CONFIGURATION METADATA")
        print(border)
        print(f"  {'Setting Parameter':<25} | {'Environment Value':<35}")
        print(thin_border)
        print(f"  {'MODEL_NAME':<25} | {config.model_name:<35}")
        print(f"  {'IMAGE_SIZE':<25} | {config.image_size:<35}")
        print(f"  {'BATCH_SIZE':<25} | {config.batch_size:<35}")
        print(f"  {'EPOCHS':<25} | {config.epochs:<35}")
        print(f"  {'DEVICE':<25} | {config.device:<35}")
        print(f"  {'WORKERS':<25} | {config.workers:<35}")
        print(f"  {'PROJECT_NAME':<25} | {config.project_name:<35}")
        print(f"  {'RUN_NAME':<25} | {config.run_name:<35}")
        print(f"  {'OUTPUT_DIRECTORY':<25} | {str(config.output_directory):<35}")
        print(f"  {'RESUME_TRAINING':<25} | {str(config.resume_training):<35}")
        print(f"  {'SEED':<25} | {config.seed:<35}")
        print(thin_border)
        print(f"  {'SKU110K_DATASET_PATH':<25} | {str(config.sku110k_dataset_path):<35}")
        print(border + "\n")

        logger.info("Training Infrastructure Ready")

        print("✅ Training configuration loaded successfully with 0 hardcoded values.\n")
        return 0

    except Exception as err:
        logger.error(f"Configuration load failed: {err}")
        print(f"\n❌ Error loading training configuration: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
