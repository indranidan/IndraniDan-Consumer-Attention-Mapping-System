"""
Module 4 — Camera Attention Heatmap Generator
===============================================
Generates 2D spatial attention density maps in camera-specific coordinate space.
Does not mix coordinates across different cameras.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
import numpy as np

from app.modules.attention.models import AttentionEventRecord


class Module4HeatmapGenerator:
    """Generates 2D attention spatial density heatmaps."""

    def __init__(self, default_width: int = 1280, default_height: int = 720):
        self.default_width = default_width
        self.default_height = default_height

    def generate_heatmap_data(
        self,
        events: List[AttentionEventRecord],
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate spatial density points and bounding statistics for web frontend rendering.
        """
        w = width or self.default_width
        h = height or self.default_height

        density_points = []
        for ev in events:
            gx, gy = None, None
            if ev.gaze_origin:
                gx, gy = ev.gaze_origin
            
            if gx is not None and gy is not None:
                # If direction is available, project point along direction
                if ev.gaze_direction:
                    dx, dy = ev.gaze_direction
                    proj_x = int(np.clip(gx + dx * 100, 0, w - 1))
                    proj_y = int(np.clip(gy + dy * 100, 0, h - 1))
                else:
                    proj_x = int(np.clip(gx, 0, w - 1))
                    proj_y = int(np.clip(gy, 0, h - 1))

                weight = ev.duration_seconds or 1.0
                density_points.append({
                    "x": proj_x,
                    "y": proj_y,
                    "weight": round(weight, 2),
                    "target_id": ev.target_id,
                    "target_name": ev.target_name,
                    "track_id": ev.track_id,
                })

        return {
            "camera_width": w,
            "camera_height": h,
            "total_points": len(density_points),
            "points": density_points,
        }

    def render_heatmap_image(
        self,
        events: List[AttentionEventRecord],
        output_image_path: Path,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[Path]:
        """
        Render a 2D Gaussian attention heatmap as a PNG image.
        """
        w = width or self.default_width
        h = height or self.default_height

        if not events:
            return None

        heat_matrix = np.zeros((h, w), dtype=np.float32)
        radius = 40
        points_added = 0

        for ev in events:
            gx, gy = None, None
            if ev.gaze_origin:
                gx, gy = ev.gaze_origin

            if gx is not None and gy is not None:
                if ev.gaze_direction:
                    dx, dy = ev.gaze_direction
                    px = int(np.clip(gx + dx * 80, 0, w - 1))
                    py = int(np.clip(gy + dy * 80, 0, h - 1))
                else:
                    px = int(np.clip(gx, 0, w - 1))
                    py = int(np.clip(gy, 0, h - 1))

                dur = float(ev.duration_seconds or 1.0)
                cv2.circle(heat_matrix, (px, py), radius, dur, -1)
                points_added += 1

        if points_added == 0:
            return None

        # Apply Gaussian Blur
        heat_matrix = cv2.GaussianBlur(heat_matrix, (0, 0), sigmaX=25, sigmaY=25)
        max_val = np.max(heat_matrix)
        if max_val > 0:
            norm_heat = (heat_matrix / max_val * 255.0).astype(np.uint8)
        else:
            norm_heat = heat_matrix.astype(np.uint8)

        colored_heat = cv2.applyColorMap(norm_heat, cv2.COLORMAP_JET)

        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_image_path), colored_heat)
        return output_image_path
