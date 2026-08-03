"""
AI Module — Dataset Validator (CLI Entry Point)
=================================================
Validates the COCO 2017 and SKU110K datasets.

Usage::

    python ai/verify_dataset.py

Prints a professional validation report and exits with
code 0 on success, code 1 on failure.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `ai.*` imports work
# when running this script directly with `python ai/verify_dataset.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.config import load_config
from ai.dataset import validate_coco_dataset, validate_sku110k_dataset
from ai.utils import print_banner, setup_logger

logger = setup_logger(__name__)


def main() -> int:
    """
    Run dataset validation and print the report.

    Returns
    -------
    int
        0 if all checks pass, 1 otherwise.
    """
    print_banner("CONSUMER ATTENTION MAPPING SYSTEM — Dataset Validator")

    # ── Load configuration ────────────────────────────────────
    logger.info("Loading Environment...")
    try:
        config = load_config()
    except RuntimeError as exc:
        logger.error(f"Failed to load configuration: {exc}")
        return 1
    except Exception as exc:
        logger.error(f"Failed to load configuration: {exc}")
        return 1

    logger.info("Configuration loaded successfully")
    logger.info(f"  COCO Path   : {config.coco_dataset_path}")
    logger.info(f"  SKU110K Path: {config.sku110k_dataset_path}")
    print()

    # ── COCO Validation ───────────────────────────────────────
    logger.info("Validating COCO 2017 Dataset...")
    coco_report = validate_coco_dataset(config)
    print()
    print(coco_report.summary())
    print()

    # ── SKU110K Validation ────────────────────────────────────
    logger.info("Validating SKU110K Dataset...")
    sku_report = validate_sku110k_dataset(config)
    print()
    print(sku_report.summary())
    print()

    # ── Final verdict ─────────────────────────────────────────
    all_passed = coco_report.passed and sku_report.passed

    width = 60
    border = "═" * width

    if all_passed:
        print(border)
        print("  ✅ Dataset Validation: PASSED")
        print(border)
        logger.info("Dataset Verified")
    else:
        print(border)
        print("  ❌ Dataset Validation: FAILED")
        print(border)
        print()
        if not coco_report.passed:
            print("  COCO 2017 issues:")
            for check in coco_report.checks:
                if not check.passed:
                    print(f"    • {check.message}")
                    if check.detail:
                        print(f"      → {check.detail}")
        if not sku_report.passed:
            print("  SKU110K issues:")
            for check in sku_report.checks:
                if not check.passed:
                    print(f"    • {check.message}")
                    if check.detail:
                        print(f"      → {check.detail}")
        print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
