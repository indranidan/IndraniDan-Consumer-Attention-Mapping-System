"""
Module 4 — Product Attention Detector
=======================================
Associates estimated viewing direction with specific products if and only if
reliable product spatial coordinates (bounding boxes or polygons) are configured.

If spatial product data is absent, product attention is cleanly marked as
"Unavailable / Not Configured" — NO fictitious product focus is ever fabricated.
"""

import math
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.modules.attention.models import GazeEstimate, ProductAttention


class ConfiguredProductRegion:
    """A configured spatial region for an individual product on a shelf."""

    def __init__(
        self,
        product_id: str,
        name: str,
        polygon: List[Tuple[int, int]],
        sku: Optional[str] = None,
        shelf_id: Optional[str] = None,
        shelf_name: Optional[str] = None,
    ):
        self.product_id = product_id
        self.name = name
        self.sku = sku
        self.shelf_id = shelf_id
        self.shelf_name = shelf_name
        self.polygon = polygon

        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        self.center = (int(sum(xs) / max(1, len(xs))), int(sum(ys) / max(1, len(ys))))
        self.contour = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))

    def contains_point(self, x: int, y: int) -> bool:
        return cv2.pointPolygonTest(self.contour, (float(x), float(y)), False) >= 0


class Module4ProductAttentionDetector:
    """
    Evaluates product-level attention when spatial product mapping exists.
    """

    def __init__(
        self,
        max_ray_distance: int = 400,
        ray_step_size: int = 15,
    ):
        self.max_ray_distance = max_ray_distance
        self.ray_step_size = ray_step_size
        self.product_regions: Dict[str, ConfiguredProductRegion] = {}
        self.is_configured: bool = False

    def load_product_mappings(self, product_mapping_list: List[dict]) -> None:
        """
        Load spatial product polygon mappings for the active camera.
        """
        self.product_regions.clear()
        if not product_mapping_list:
            self.is_configured = False
            return

        for p in product_mapping_list:
            p_id = p.get("product_id") or p.get("id")
            p_name = p.get("name") or p.get("product_name")
            p_poly = p.get("polygon") or p.get("bbox_polygon")
            if p_id and p_name and p_poly and len(p_poly) >= 3:
                poly = [(int(pt[0]), int(pt[1])) for pt in p_poly]
                self.product_regions[str(p_id)] = ConfiguredProductRegion(
                    product_id=str(p_id),
                    name=str(p_name),
                    polygon=poly,
                    sku=p.get("sku"),
                    shelf_id=p.get("shelf_id"),
                    shelf_name=p.get("shelf_name"),
                )

        self.is_configured = len(self.product_regions) > 0

    def find_focused_product(
        self,
        gaze: GazeEstimate,
        parent_shelf_id: Optional[str] = None,
    ) -> Optional[ConfiguredProductRegion]:
        """
        Find specific product intersecting the gaze ray.
        Returns None if product mapping is unconfigured or gaze does not intersect.
        """
        if not self.is_configured or not gaze.is_valid or not self.product_regions:
            return None

        ox, oy = gaze.origin
        dx, dy = gaze.direction

        # Filter candidates by shelf if specified
        candidates_pool = list(self.product_regions.values())
        if parent_shelf_id:
            matching_shelf = [p for p in candidates_pool if p.shelf_id == parent_shelf_id]
            if matching_shelf:
                candidates_pool = matching_shelf

        # Ray check
        num_steps = max(1, self.max_ray_distance // self.ray_step_size)
        candidates: List[Tuple[float, float, ConfiguredProductRegion]] = []

        for prod in candidates_pool:
            for step in range(1, num_steps + 1):
                sx = int(ox + dx * step * self.ray_step_size)
                sy = int(oy + dy * step * self.ray_step_size)
                if prod.contains_point(sx, sy):
                    dist = step * self.ray_step_size
                    # Alignment score
                    to_cx = prod.center[0] - ox
                    to_cy = prod.center[1] - oy
                    d_c = math.hypot(to_cx, to_cy)
                    score = (dx * (to_cx / d_c) + dy * (to_cy / d_c)) if d_c > 0 else 1.0
                    candidates.append((dist, score, prod))
                    break

        if not candidates:
            return None

        candidates.sort(key=lambda c: (-c[1], c[0]))
        return candidates[0][2]

    def get_unconfigured_placeholder(self, product_list: Optional[List[dict]] = None) -> List[ProductAttention]:
        """
        Return structured ProductAttention items marked clearly as 'Unavailable / Not Configured'.
        """
        if not product_list:
            return []

        results = []
        for p in product_list:
            results.append(
                ProductAttention(
                    product_id=str(p.get("id", "")),
                    product_name=str(p.get("name", "Unknown Product")),
                    sku=p.get("sku"),
                    shelf_id=str(p.get("shelf_id", "")),
                    is_configured=False,
                    viewers=0,
                    attention_events=0,
                    total_focus_duration_sec=0.0,
                    average_focus_duration_sec=0.0,
                    repeated_attention_events=0,
                    status_note="Unavailable / Not Configured (No spatial polygon mapped)",
                )
            )
        return results
