"""
Attention Analysis — Attention Region Manager
================================================
Loads and manages attention target regions (shelves, zones, products) from
a JSON configuration file. Provides ray-polygon intersection tests to
determine whether a shopper's estimated attention direction intersects
a configured retail region.

Region coordinates are NOT hardcoded. They are loaded from a configurable
JSON file (default: configs/attention_regions.json).
"""

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.logger import setup_logger


@dataclass
class AttentionRegion:
    """A configured attention target region (shelf, zone, or product)."""

    id: str
    name: str
    type: str  # "shelf", "zone", "product"
    polygon: List[Tuple[int, int]]
    center: Tuple[int, int] = field(init=False)
    _contour: Optional[np.ndarray] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Compute the polygon center and OpenCV contour."""
        xs = [p[0] for p in self.polygon]
        ys = [p[1] for p in self.polygon]
        self.center = (
            int(sum(xs) / len(xs)),
            int(sum(ys) / len(ys)),
        )
        self._contour = np.array(self.polygon, dtype=np.int32).reshape((-1, 1, 2))

    @property
    def contour(self) -> np.ndarray:
        """Return the pre-computed OpenCV contour for this region polygon."""
        return self._contour


class AttentionRegionManager:
    """
    Manages attention target regions loaded from a JSON configuration file.

    Provides spatial queries for ray-polygon intersection to determine
    whether a shopper's estimated attention direction intersects a
    configured retail region.
    """

    def __init__(
        self,
        config_path: Path,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the attention region manager.

        Parameters
        ----------
        config_path : Path
            Path to the attention_regions.json configuration file.
        logger : logging.Logger, optional
            Logger instance.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        ValueError
            If the configuration is invalid.
        """
        self.config_path = config_path
        self.logger = logger or setup_logger("attention_region_manager")
        self.regions: Dict[str, AttentionRegion] = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load and validate attention region configuration from JSON."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Attention region config not found: {self.config_path}\n"
                f"Create an attention_regions.json file or update "
                f"ATTENTION_REGIONS_PATH in .env."
            )

        self.logger.info(f"Loading attention regions from: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in attention region config: {self.config_path}\n"
                f"Error: {exc}"
            ) from exc

        raw_regions = config_data.get("regions", [])
        if not raw_regions:
            self.logger.warning("No attention regions defined in configuration.")
            return

        for region_data in raw_regions:
            region = self._parse_region(region_data)
            self.regions[region.id] = region

        self.logger.info(f"Attention regions loaded: {len(self.regions)}")

    def _parse_region(self, data: dict) -> AttentionRegion:
        """
        Parse and validate a single attention region definition.

        Parameters
        ----------
        data : dict
            Raw JSON region data.

        Returns
        -------
        AttentionRegion
            Validated region definition.

        Raises
        ------
        ValueError
            If required fields are missing or polygon is invalid.
        """
        region_id = data.get("id")
        region_name = data.get("name")
        region_type = data.get("type", "shelf")
        raw_polygon = data.get("polygon")

        if not region_id:
            raise ValueError(f"Missing 'id' field in attention region: {data}")
        if not region_name:
            raise ValueError(f"Missing 'name' field in attention region '{region_id}'")
        if not raw_polygon:
            raise ValueError(
                f"Missing 'polygon' field in attention region '{region_id}'"
            )

        # Validate polygon
        self._validate_polygon(raw_polygon, region_id)

        polygon = [(int(p[0]), int(p[1])) for p in raw_polygon]

        return AttentionRegion(
            id=region_id,
            name=region_name,
            type=region_type,
            polygon=polygon,
        )

    def _validate_polygon(self, polygon: list, region_id: str) -> None:
        """Validate polygon geometry."""
        if len(polygon) < 3:
            raise ValueError(
                f"Invalid polygon for attention region '{region_id}': "
                f"requires at least 3 vertices, got {len(polygon)}."
            )

        for i, point in enumerate(polygon):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(
                    f"Invalid vertex {i} in attention region '{region_id}': "
                    f"expected [x, y], got {point}"
                )
            try:
                int(point[0])
                int(point[1])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Non-numeric coordinate at vertex {i} in attention region "
                    f"'{region_id}': {point}"
                ) from exc

    def get_all_regions(self) -> List[AttentionRegion]:
        """Return all configured attention regions."""
        return list(self.regions.values())

    def get_region(self, region_id: str) -> Optional[AttentionRegion]:
        """Get a specific region by ID."""
        return self.regions.get(region_id)

    def point_in_region(self, x: int, y: int, region: AttentionRegion) -> bool:
        """Test whether a point is inside a region polygon."""
        result = cv2.pointPolygonTest(
            region.contour, (float(x), float(y)), False
        )
        return result >= 0

    def find_attention_target(
        self,
        head_x: int,
        head_y: int,
        yaw: float,
        pitch: float,
        max_distance: int,
    ) -> Optional[AttentionRegion]:
        """
        Find the attention target region that best matches the shopper's
        estimated attention direction.

        Uses a geometric ray-cone approach:
        1. Compute a direction vector from the head pose angles
        2. Cast sample points along the ray
        3. Check if any sample point falls inside a configured region
        4. If multiple regions match: prefer highest geometric alignment,
           then closest valid target

        Parameters
        ----------
        head_x : int
            X coordinate of the shopper's head/nose in frame space.
        head_y : int
            Y coordinate of the shopper's head/nose in frame space.
        yaw : float
            Head yaw angle in degrees.
        pitch : float
            Head pitch angle in degrees.
        max_distance : int
            Maximum ray length in pixels.

        Returns
        -------
        Optional[AttentionRegion]
            The best matching attention target, or None if no region
            can be reliably associated.
        """
        if not self.regions:
            return None

        # Convert yaw/pitch to a 2D direction vector in image space
        # Yaw: positive = right, Pitch: positive = up (in 3D), but
        # in image space Y increases downward
        yaw_rad = math.radians(yaw)
        pitch_rad = math.radians(-pitch)  # Invert for image coordinates

        dx = math.sin(yaw_rad)
        dy = math.sin(pitch_rad)

        # Normalize direction vector
        magnitude = math.sqrt(dx * dx + dy * dy)
        if magnitude < 0.15:  # Near-zero direction (CENTER / looking forward)
            # 1. First check if head position is directly inside any region
            for region in self.regions.values():
                if self.point_in_region(head_x, head_y, region):
                    return region

            # 2. Check closest region center within proximity threshold (e.g. 300px)
            closest_region = None
            min_dist = float("inf")
            for region in self.regions.values():
                to_cx = region.center[0] - head_x
                to_cy = region.center[1] - head_y
                dist = math.sqrt(to_cx * to_cx + to_cy * to_cy)
                if dist <= max_distance and dist < min_dist:
                    min_dist = dist
                    closest_region = region
            return closest_region

        dx /= magnitude
        dy /= magnitude

        # Cast ray: sample points at intervals along the direction
        step_size = 20  # pixels per step
        num_steps = max(1, max_distance // step_size)

        # Track candidates: (distance, alignment_score, region)
        candidates: List[Tuple[float, float, AttentionRegion]] = []

        for region in self.regions.values():
            best_distance = None

            # Check ray sample points
            for step in range(1, num_steps + 1):
                sample_x = int(head_x + dx * step * step_size)
                sample_y = int(head_y + dy * step * step_size)

                if self.point_in_region(sample_x, sample_y, region):
                    distance = step * step_size
                    best_distance = distance
                    break

            # Also check if the region center is roughly in the gaze direction
            if best_distance is None:
                # Vector from head to region center
                to_center_x = region.center[0] - head_x
                to_center_y = region.center[1] - head_y
                dist_to_center = math.sqrt(
                    to_center_x ** 2 + to_center_y ** 2
                )

                if dist_to_center > 0 and dist_to_center <= max_distance:
                    # Dot product for alignment
                    tc_dx = to_center_x / dist_to_center
                    tc_dy = to_center_y / dist_to_center
                    alignment = dx * tc_dx + dy * tc_dy

                    # Only consider if alignment is reasonably good (> 0.5)
                    if alignment > 0.5:
                        # Check if the projected point lands inside the region
                        proj_dist = dist_to_center * alignment
                        proj_x = int(head_x + dx * proj_dist)
                        proj_y = int(head_y + dy * proj_dist)

                        if self.point_in_region(proj_x, proj_y, region):
                            best_distance = proj_dist

            if best_distance is not None:
                # Alignment score: how well does the gaze direction point
                # toward the region center
                to_center_x = region.center[0] - head_x
                to_center_y = region.center[1] - head_y
                dist_to_center = math.sqrt(
                    to_center_x ** 2 + to_center_y ** 2
                )
                if dist_to_center > 0:
                    alignment_score = (
                        dx * (to_center_x / dist_to_center)
                        + dy * (to_center_y / dist_to_center)
                    )
                else:
                    alignment_score = 1.0

                candidates.append(
                    (best_distance, alignment_score, region)
                )

        if not candidates:
            return None

        # Deterministic selection:
        # 1. Highest geometric alignment
        # 2. Closest valid target
        candidates.sort(key=lambda c: (-c[1], c[0]))
        return candidates[0][2]
