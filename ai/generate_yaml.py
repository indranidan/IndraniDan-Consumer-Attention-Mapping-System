"""
AI Module — Dynamic data.yaml Generator
========================================
Dynamically generates ai/configs/sku110k.yaml using paths read from .env.
Validates dataset structure and YAML format before saving.

Usage:
    python ai/generate_yaml.py
"""

import sys
from pathlib import Path
import yaml

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import load_config
from ai.logger import setup_logger
from ai.utils import ensure_directory, print_banner

logger = setup_logger("generate_yaml")


def generate_sku110k_yaml() -> Path:
    """
    Generate and validate sku110k.yaml configuration file for YOLOv8 training.

    Returns:
        Path: Absolute path to the generated YAML file.

    Raises:
        RuntimeError: If configuration is invalid or dataset path missing.
    """
    logger.info("Loading Environment...")
    logger.info("Reading .env...")

    config = load_config()

    sku_dataset_path = config.sku110k_dataset_path

    if not sku_dataset_path.exists():
        raise RuntimeError(
            f"SKU-110K dataset directory not found at: {sku_dataset_path}\n"
            f"Check SKU110K_DATASET_PATH in .env"
        )

    # Ensure configs directory exists
    configs_dir = ensure_directory(config.configs_dir)
    target_yaml_path = configs_dir / "sku110k.yaml"

    yaml_data = {
        "path": str(sku_dataset_path.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,
        "names": {0: "object"},
    }

    logger.info("Generating data.yaml...")

    # Validate structure by dumping and reloading in memory
    try:
        raw_yaml = yaml.dump(yaml_data, sort_keys=False, default_flow_style=False)
        parsed_data = yaml.safe_load(raw_yaml)

        # Validate required YOLO keys
        required_keys = ["path", "train", "val", "nc", "names"]
        for key in required_keys:
            if key not in parsed_data:
                raise ValueError(f"Generated YAML missing required key: '{key}'")

        if parsed_data["nc"] != 1:
            raise ValueError(f"Invalid class count 'nc': {parsed_data['nc']}, expected 1")

    except Exception as exc:
        raise RuntimeError(f"YAML validation error before saving: {exc}")

    # Write YAML file
    try:
        with open(target_yaml_path, "w", encoding="utf-8") as f:
            f.write("# YOLOv8 Dataset Configuration for SKU-110K\n")
            f.write("# Generated automatically from .env configuration\n\n")
            yaml.dump(yaml_data, f, sort_keys=False, default_flow_style=False)

        logger.info(f"Successfully saved YAML to: {target_yaml_path}")

    except Exception as exc:
        raise RuntimeError(f"Failed to write YAML file to {target_yaml_path}: {exc}")

    # Final verify read
    with open(target_yaml_path, "r", encoding="utf-8") as f:
        verified_data = yaml.safe_load(f)

    if not verified_data or verified_data.get("nc") != 1:
        raise RuntimeError(f"Written YAML file verification failed at {target_yaml_path}")

    return target_yaml_path


def main() -> int:
    """CLI entry point for generating data.yaml."""
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — Generate data.yaml")

    try:
        yaml_path = generate_sku110k_yaml()
        print(f"\n✅ Dynamic data.yaml successfully generated at:\n   {yaml_path}\n")
        return 0
    except Exception as err:
        logger.error(f"Failed to generate data.yaml: {err}")
        print(f"\n❌ Error generating data.yaml: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
