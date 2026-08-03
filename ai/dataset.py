"""
AI Module — Dataset Handling
==============================
Resolves and validates the COCO 2017 and SKU110K dataset structures.
Handles nested directory layouts and verifies complete image-label pairings.
"""

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai.config import AIConfig, load_config
from ai.utils import setup_logger

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str
    detail: str = ""


@dataclass
class ValidationReport:
    """Aggregated validation report."""

    dataset_name: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def add(self, name: str, passed: bool, message: str, detail: str = "") -> None:
        self.checks.append(CheckResult(name=name, passed=passed, message=message, detail=detail))

    def summary(self) -> str:
        lines: List[str] = []
        for check in self.checks:
            icon = "[✔]" if check.passed else "[✘]"
            lines.append(f"  {icon} {check.message}")
            if check.detail and not check.passed:
                lines.append(f"      → {check.detail}")
        return "\n".join(lines)


@dataclass
class SKU110KSplitStats:
    """Statistics for a single dataset split (train, val, test)."""

    split: str
    images_count: int = 0
    labels_count: int = 0
    matched_count: int = 0
    missing_labels: List[str] = field(default_factory=list)
    unmatched_labels: List[str] = field(default_factory=list)
    corrupted_labels: List[str] = field(default_factory=list)


@dataclass
class SKU110KStats:
    """Aggregated statistics across all SKU110K splits."""

    root_path: Path
    splits: Dict[str, SKU110KSplitStats] = field(
        default_factory=lambda: {
            "train": SKU110KSplitStats("train"),
            "val": SKU110KSplitStats("val"),
            "test": SKU110KSplitStats("test"),
        }
    )
    passed: bool = False
    error_message: str = ""


# ---------------------------------------------------------------------------
# COCO path resolution & validation
# ---------------------------------------------------------------------------
@dataclass
class COCOPaths:
    """Resolved paths for the COCO 2017 dataset."""

    root: Path
    train_images: Path
    val_images: Path
    annotations_dir: Path

    instances_train: Path = field(init=False)
    instances_val: Path = field(init=False)
    captions_train: Path = field(init=False)
    captions_val: Path = field(init=False)
    keypoints_train: Path = field(init=False)
    keypoints_val: Path = field(init=False)

    def __post_init__(self) -> None:
        self.instances_train = self.annotations_dir / "instances_train2017.json"
        self.instances_val = self.annotations_dir / "instances_val2017.json"
        self.captions_train = self.annotations_dir / "captions_train2017.json"
        self.captions_val = self.annotations_dir / "captions_val2017.json"
        self.keypoints_train = self.annotations_dir / "person_keypoints_train2017.json"
        self.keypoints_val = self.annotations_dir / "person_keypoints_val2017.json"


def _find_image_dir(base: Path, name: str) -> Optional[Path]:
    nested = base / name / name
    flat = base / name
    if nested.is_dir():
        return nested
    if flat.is_dir():
        return flat
    return None


def _find_annotations_dir(base: Path) -> Optional[Path]:
    nested = base / "annotations_trainval2017" / "annotations"
    flat = base / "annotations"
    if nested.is_dir():
        return nested
    if flat.is_dir():
        return flat
    return None


def resolve_coco_paths(coco_root: Path) -> Optional[COCOPaths]:
    if not coco_root.is_dir():
        return None

    train_dir = _find_image_dir(coco_root, "train2017")
    val_dir = _find_image_dir(coco_root, "val2017")
    ann_dir = _find_annotations_dir(coco_root)

    if not train_dir or not val_dir or not ann_dir:
        return COCOPaths(
            root=coco_root,
            train_images=train_dir or coco_root / "train2017",
            val_images=val_dir or coco_root / "val2017",
            annotations_dir=ann_dir or coco_root / "annotations",
        )

    return COCOPaths(
        root=coco_root,
        train_images=train_dir,
        val_images=val_dir,
        annotations_dir=ann_dir,
    )


def _count_images(directory: Path, extensions: tuple = (".jpg", ".jpeg", ".png")) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for f in directory.iterdir() if f.suffix.lower() in extensions)


def _load_json_safe(path: Path) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    if not path.exists():
        return False, f"File not found: {path}", None
    if not path.is_file():
        return False, f"Not a file: {path}", None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return True, "OK", data
    except json.JSONDecodeError as exc:
        return False, f"Invalid JSON in {path.name}: {exc}", None
    except PermissionError:
        return False, f"Permission denied: {path}", None
    except OSError as exc:
        return False, f"OS error reading {path.name}: {exc}", None


def validate_coco_dataset(config: AIConfig) -> ValidationReport:
    report = ValidationReport(dataset_name="COCO 2017")
    coco_root = config.coco_dataset_path
    report.add(
        name="root_exists",
        passed=coco_root.is_dir(),
        message=f"COCO dataset path exists: {coco_root}",
        detail=f"Directory not found: {coco_root}",
    )
    if not coco_root.is_dir():
        return report

    paths = resolve_coco_paths(coco_root)
    if paths is None:
        report.add("resolve", False, "Failed to resolve COCO paths")
        return report

    train_exists = paths.train_images.is_dir()
    train_count = _count_images(paths.train_images) if train_exists else 0
    report.add(
        name="train2017",
        passed=train_exists and train_count > 0,
        message=f"train2017 directory found ({train_count:,} images)" if train_exists else "train2017 directory missing",
        detail=f"Expected at: {paths.train_images}",
    )

    val_exists = paths.val_images.is_dir()
    val_count = _count_images(paths.val_images) if val_exists else 0
    report.add(
        name="val2017",
        passed=val_exists and val_count > 0,
        message=f"val2017 directory found ({val_count:,} images)" if val_exists else "val2017 directory missing",
        detail=f"Expected at: {paths.val_images}",
    )

    ann_exists = paths.annotations_dir.is_dir()
    report.add(
        name="annotations_dir",
        passed=ann_exists,
        message=f"Annotations directory found: {paths.annotations_dir}" if ann_exists else "Annotations directory missing",
        detail=f"Checked: {coco_root / 'annotations_trainval2017' / 'annotations'} and {coco_root / 'annotations'}",
    )
    if not ann_exists:
        return report

    ok, msg, data = _load_json_safe(paths.instances_train)
    ann_count = len(data.get("annotations", [])) if data else 0
    report.add(
        name="instances_train",
        passed=ok,
        message=f"instances_train2017.json loaded ({ann_count:,} annotations)" if ok else f"instances_train2017.json — {msg}",
        detail=msg if not ok else "",
    )

    ok, msg, data = _load_json_safe(paths.instances_val)
    ann_count = len(data.get("annotations", [])) if data else 0
    report.add(
        name="instances_val",
        passed=ok,
        message=f"instances_val2017.json loaded ({ann_count:,} annotations)" if ok else f"instances_val2017.json — {msg}",
        detail=msg if not ok else "",
    )

    return report


# ---------------------------------------------------------------------------
# Comprehensive SKU110K Dataset Verification & Statistics
# ---------------------------------------------------------------------------
def verify_and_count_sku110k(sku_root: Path) -> Tuple[ValidationReport, SKU110KStats]:
    """
    Comprehensive verification and statistics collection for SKU-110K dataset.

    Checks:
    - Root exists
    - images/ and labels/ directories exist
    - train, val, test subdirectories exist in both images/ and labels/
    - Counts images and labels per split
    - Verifies image to label matching
    - Detects empty directories or missing/corrupted files
    """
    report = ValidationReport(dataset_name="SKU110K")
    stats = SKU110KStats(root_path=sku_root)

    # 1. Root directory check
    if not sku_root.exists():
        msg = f"Dataset path does not exist: {sku_root}"
        report.add("root_exists", False, msg)
        stats.error_message = msg
        return report, stats

    if not sku_root.is_dir():
        msg = f"Dataset path is not a directory: {sku_root}"
        report.add("root_is_dir", False, msg)
        stats.error_message = msg
        return report, stats

    report.add("root_exists", True, f"SKU110K root directory exists: {sku_root}")

    # 2. Main images and labels directories
    images_dir = sku_root / "images"
    labels_dir = sku_root / "labels"

    report.add("images_dir", images_dir.is_dir(), f"images/ directory found" if images_dir.is_dir() else "images/ directory missing")
    report.add("labels_dir", labels_dir.is_dir(), f"labels/ directory found" if labels_dir.is_dir() else "labels/ directory missing")

    if not (images_dir.is_dir() and labels_dir.is_dir()):
        stats.error_message = "Missing images/ or labels/ root directory"
        return report, stats

    # 3. Splits verification (train, val, test)
    splits = ["train", "val", "test"]
    image_exts = {".jpg", ".jpeg", ".png"}

    for split in splits:
        img_split_dir = images_dir / split
        lbl_split_dir = labels_dir / split

        img_split_exists = img_split_dir.is_dir()
        lbl_split_exists = lbl_split_dir.is_dir()

        report.add(
            f"images_{split}_exists",
            img_split_exists,
            f"images/{split}/ directory exists" if img_split_exists else f"images/{split}/ directory missing",
        )
        report.add(
            f"labels_{split}_exists",
            lbl_split_exists,
            f"labels/{split}/ directory exists" if lbl_split_exists else f"labels/{split}/ directory missing",
        )

        if not (img_split_exists and lbl_split_exists):
            continue

        split_stats = stats.splits[split]

        # Collect images and labels map {stem: Path}
        try:
            image_files = {
                f.stem: f for f in img_split_dir.iterdir()
                if f.is_file() and f.suffix.lower() in image_exts
            }
            label_files = {
                f.stem: f for f in lbl_split_dir.iterdir()
                if f.is_file() and f.suffix.lower() == ".txt"
            }
        except PermissionError as pe:
            report.add(f"{split}_permission", False, f"Permission error reading {split}: {pe}")
            continue

        split_stats.images_count = len(image_files)
        split_stats.labels_count = len(label_files)

        # Check empty split directories
        if split_stats.images_count == 0:
            report.add(f"images_{split}_nonempty", False, f"images/{split}/ is empty!")
        else:
            report.add(f"images_{split}_count", True, f"images/{split}/ contains {split_stats.images_count:,} images")

        if split_stats.labels_count == 0:
            report.add(f"labels_{split}_nonempty", False, f"labels/{split}/ is empty!")
        else:
            report.add(f"labels_{split}_count", True, f"labels/{split}/ contains {split_stats.labels_count:,} labels")

        # Match check
        matched = 0
        for stem, img_path in image_files.items():
            if stem in label_files:
                matched += 1
                # Check label file corruption (zero size or non-readable)
                lbl_path = label_files[stem]
                try:
                    if lbl_path.stat().st_size == 0:
                        # Zero-size label file (could be background image, but note if corrupted)
                        pass
                except Exception:
                    split_stats.corrupted_labels.append(lbl_path.name)
            else:
                split_stats.missing_labels.append(img_path.name)

        split_stats.matched_count = matched

        for stem, lbl_path in label_files.items():
            if stem not in image_files:
                split_stats.unmatched_labels.append(lbl_path.name)

        matches_perfect = (matched == split_stats.images_count) and (len(split_stats.unmatched_labels) == 0)
        report.add(
            f"{split}_matching",
            matches_perfect,
            f"{split} split: All {matched:,} images have matching label files"
            if matches_perfect
            else f"{split} split: Match issue! Matched {matched:,}/{split_stats.images_count:,} images. Missing labels: {len(split_stats.missing_labels)}, Unmatched labels: {len(split_stats.unmatched_labels)}",
        )

    stats.passed = report.passed
    return report, stats


def validate_sku110k_dataset(config: AIConfig) -> ValidationReport:
    """
    Validate the SKU110K dataset using AIConfig.

    Parameters
    ----------
    config : AIConfig

    Returns
    -------
    ValidationReport
    """
    report, _ = verify_and_count_sku110k(config.sku110k_dataset_path)
    return report


def get_random_val_images(config: AIConfig, n: int = 5) -> List[Path]:
    """
    Sample n random images from the COCO val2017 set.
    """
    paths = resolve_coco_paths(config.coco_dataset_path)
    if paths is None or not paths.val_images.is_dir():
        raise FileNotFoundError(
            f"COCO val2017 images not found. Check COCO_DATASET_PATH in .env.\n"
            f"Expected at: {config.coco_dataset_path}"
        )

    images = [
        p for p in paths.val_images.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png")
    ]

    if not images:
        raise FileNotFoundError(f"No images found in {paths.val_images}")

    n = min(n, len(images))
    sampled = random.sample(images, n)
    logger.info(f"Sampled {n} images from val2017 ({len(images):,} total)")
    return sampled
