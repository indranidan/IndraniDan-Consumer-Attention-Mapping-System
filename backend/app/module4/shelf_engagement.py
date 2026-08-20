"""
Module 4 — Shelf Engagement Analysis
======================================
Associates shopper's estimated viewing direction with configured shelf regions.
Enforces the critical condition that presence in a zone != shelf attention.
"""

import math
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.module4.models import GazeEstimate


class ConfiguredRegion:
    """A configured spatial region (shelf, zone, product, display)."""

    def __init__(
        self,
        region_id: str,
        name: str,
        region_type: str,
        polygon: List[Tuple[int, int]],
        shelf_code: Optional[str] = None,
    ):
        self.id = region_id
        self.name = name
        self.type = region_type
        self.polygon = polygon
        self.shelf_code = shelf_code

        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        self.center = (int(sum(xs) / max(1, len(xs))), int(sum(ys) / max(1, len(ys))))
        self.contour = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))

    def contains_point(self, x: int, y: int) -> bool:
        """Point-in-polygon test."""
        return cv2.pointPolygonTest(self.contour, (float(x), float(y)), False) >= 0


class Module4ShelfEngagementAnalyzer:
    """
    Evaluates whether a shopper is actively viewing a configured shelf region.
    """

    def __init__(
        self,
        max_ray_distance: int = 500,
        ray_step_size: int = 20,
        alignment_threshold: float = 0.5,
    ):
        self.max_ray_distance = max_ray_distance
        self.ray_step_size = ray_step_size
        self.alignment_threshold = alignment_threshold
        self.regions: Dict[str, ConfiguredRegion] = {}

    def register_region(
        self,
        region_id: str,
        name: str,
        region_type: str,
        polygon: List[Tuple[int, int]],
        shelf_code: Optional[str] = None,
    ) -> None:
        """Register or update a configured spatial region."""
        self.regions[region_id] = ConfiguredRegion(
            region_id=region_id,
            name=name,
            region_type=region_type,
            polygon=polygon,
            shelf_code=shelf_code,
        )

    def load_from_dict_list(self, raw_regions: List[dict]) -> None:
        """Load regions from standard JSON/dict list."""
        self.regions.clear()
        for r in raw_regions:
            r_id = r.get("id") or r.get("shelf_id") or r.get("zone_id")
            r_name = r.get("name") or r.get("shelf_name") or r.get("zone_name")
            r_type = r.get("type", "shelf")
            raw_poly = r.get("polygon", [])
            if r_id and r_name and len(raw_poly) >= 3:
                poly = [(int(p[0]), int(p[1])) for p in raw_poly]
                self.register_region(
                    region_id=str(r_id),
                    name=str(r_name),
                    region_type=str(r_type),
                    polygon=poly,
                    shelf_code=r.get("shelf_code"),
                )

    def find_engaged_shelf(
        self,
        gaze: GazeEstimate,
        person_center: Tuple[int, int],
        current_zone_id: Optional[str] = None,
    ) -> Optional[ConfiguredRegion]:
        """
        Determine if the estimated gaze ray intersects a configured shelf.

        Requirements for engagement:
        1. Gaze estimate must be valid and meet confidence threshold.
        2. Gaze ray must geometrically intersect or strongly align with the shelf polygon.
        3. Simple physical presence inside a zone without gaze alignment does NOT trigger engagement.

        Parameters
        ----------
        gaze : GazeEstimate
            Estimated viewing origin and direction vector.
        person_center : Tuple[int, int]
            Center coordinates of the person bounding box.
        current_zone_id : Optional[str]
            Zone ID the person is currently located in.

        Returns
        -------
        Optional[ConfiguredRegion]
            The matched shelf region or None.
        """
        if not gaze.is_valid or not self.regions:
            return None

        ox, oy = gaze.origin
        dx, dy = gaze.direction

        # Filter only shelf / display regions
        shelf_regions = [r for r in self.regions.values() if r.type in ("shelf", "custom_zone")]
        if not shelf_regions:
            shelf_regions = list(self.regions.values())

        # If gaze direction vector is near zero (shopper looking forward in camera plane)
        mag = math.sqrt(dx * dx + dy * dy)
        if mag < 0.15:
            # Check if gaze origin is directly inside a shelf
            for region in shelf_regions:
                if region.contains_point(ox, oy):
                    return region
            # If inside zone, verify distance to shelf center is close
            for region in shelf_regions:
                dist = math.hypot(region.center[0] - ox, region.center[1] - oy)
                if dist <= 250:
                    return region
            return None

        # Ray casting
        num_steps = max(1, self.max_ray_distance // self.ray_step_size)
        candidates: List[Tuple[float, float, ConfiguredRegion]] = []

        for region in shelf_regions:
            best_distance = None

            # Sample along ray
            for step in range(1, num_steps + 1):
                sx = int(ox + dx * step * self.ray_step_size)
                sy = int(oy + dy * step * self.ray_step_size)
                if region.contains_point(sx, sy):
                    best_distance = step * self.ray_step_size
                    break

            # If ray point test didn't directly hit, check alignment toward region center
            if best_distance is None:
                to_cx = region.center[0] - ox
                to_cy = region.center[1] - oy
                dist_to_center = math.hypot(to_cx, to_cy)

                if 0 < dist_to_center <= self.max_ray_distance:
                    unit_tc_x = to_cx / dist_to_center
                    unit_tc_y = to_cy / dist_to_center
                    alignment = dx * unit_tc_x + dy * unit_tc_y

                    if alignment >= self.alignment_threshold:
                        proj_dist = dist_to_center * alignment
                        px = int(ox + dx * proj_dist)
                        py = int(oy + dy * proj_dist)
                        if region.contains_point(px, py):
                            best_distance = proj_dist

            if best_distance is not None:
                to_cx = region.center[0] - ox
                to_cy = region.center[1] - oy
                dist_to_c = math.hypot(to_cx, to_cy)
                score = (dx * (to_cx / dist_to_c) + dy * (to_cy / dist_to_c)) if dist_to_c > 0 else 1.0
                candidates.append((best_distance, score, region))

        if not candidates:
            return None

        # Sort by best alignment first, then shortest distance
        candidates.sort(key=lambda c: (-c[1], c[0]))
        return candidates[0][2]
