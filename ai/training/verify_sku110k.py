"""
=================================================
AI Module — SKU-110K Dataset Verification (CLI)
=================================================
Verifies SKU-110K dataset structure, validates image and label pairing for train, val,
and test splits, and displays complete dataset statistics.

Usage:
    python ai/verify_sku110k.py
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import load_config
from ai.dataset import verify_and_count_sku110k
from ai.logger import setup_logger
from ai.utils import print_banner, setup_output_directories

logger = setup_logger("verify_sku110k")


def main() -> int:
    """
    Run SKU-110K dataset verification.

    Returns:
        int: 0 if valid, 1 if invalid or errors encountered.
    """
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — SKU-110K Dataset Validator")

    logger.info("Loading Environment...")
    logger.info("Reading .env...")

    try:
        config = load_config()
    except RuntimeError as err:
        logger.error(f"Configuration error: {err}")
        return 1
    except Exception as err:
        logger.error(f"Failed to load .env configuration: {err}")
        return 1

    # Ensure output directories exist
    setup_output_directories(config.output_directory)

    logger.info(f"Checking dataset path: {config.sku110k_dataset_path}")

    report, stats = verify_and_count_sku110k(config.sku110k_dataset_path)

    if not stats.root_path.exists():
        logger.error(f"Dataset directory not found: {config.sku110k_dataset_path}")
        logger.error("Please verify SKU110K_DATASET_PATH in .env")
        return 1

    logger.info("Dataset Found")

    # Display detailed check results
    print("\n" + report.summary() + "\n")

    # Display dataset statistics table
    border = "═" * 70
    thin_border = "─" * 70

    print(border)
    print(f"  SKU-110K DATASET STATISTICS REPORT")
    print(border)
    print(f"  {'Split':<12} | {'Images':<12} | {'Labels':<12} | {'Matched':<12} | {'Status':<10}")
    print(thin_border)

    total_images = 0
    total_labels = 0
    total_matched = 0

    for split in ["train", "val", "test"]:
        sp_stats = stats.splits[split]
        status = "OK" if (sp_stats.matched_count == sp_stats.images_count and sp_stats.images_count > 0) else "FAIL"

        print(
            f"  {split.capitalize():<12} | "
            f"{sp_stats.images_count:<12,} | "
            f"{sp_stats.labels_count:<12,} | "
            f"{sp_stats.matched_count:<12,} | "
            f"{status:<10}"
        )

        total_images += sp_stats.images_count
        total_labels += sp_stats.labels_count
        total_matched += sp_stats.matched_count

    print(thin_border)
    print(
        f"  {'TOTAL':<12} | "
        f"{total_images:<12,} | "
        f"{total_labels:<12,} | "
        f"{total_matched:<12,} | "
        f"{'OK' if report.passed else 'FAIL':<10}"
    )
    print(border)

    if report.passed:
        logger.info("Dataset Verified successfully")
        print("\n✅ SKU-110K dataset verification PASSED! Ready for YOLOv8 training.\n")
        return 0
    else:
        logger.error("Dataset Verification FAILED")
        print("\n❌ SKU-110K dataset verification FAILED with issues listed above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
