"""
Module 7 — Attention Heatmap Engine
=====================================
Core spatial density computation engine for store-wide heatmap synthesis.

Provides:
- Multi-camera coordinate normalization to floorplan [0.0, 1.0] space.
- 2D Gaussian kernel density matrix computation.
- Configurable colormap rendering (JET, TURBO, INFERNO, VIRIDIS).
- Pre-rendered PNG heatmap image generation via OpenCV.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


# ── Colormap Registry ─────────────────────────────────────────
COLORMAP_REGISTRY = {
    "JET": cv2.COLORMAP_JET,
    "TURBO": cv2.COLORMAP_TURBO,
    "INFERNO": cv2.COLORMAP_INFERNO,
    "VIRIDIS": cv2.COLORMAP_VIRIDIS,
    "HOT": cv2.COLORMAP_HOT,
    "MAGMA": cv2.COLORMAP_MAGMA,
    "PLASMA": cv2.COLORMAP_PLASMA,
}


def normalize_camera_coords(
    points: List[Dict[str, Any]],
    camera_width: int,
    camera_height: int,
) -> List[Dict[str, float]]:
    """
    Normalize raw camera pixel coordinates to unit [0.0, 1.0] space
    relative to camera frame dimensions.

    Each input point dict must have 'x', 'y', and optionally 'weight'.
    Returns list of dicts with 'nx', 'ny', 'weight'.
    """
    if camera_width <= 0 or camera_height <= 0:
        return []

    normalized = []
    for pt in points:
        x = pt.get("x", 0)
        y = pt.get("y", 0)
        weight = pt.get("weight", 1.0)
        nx = float(np.clip(x / camera_width, 0.0, 1.0))
        ny = float(np.clip(y / camera_height, 0.0, 1.0))
        normalized.append({
            "nx": round(nx, 6),
            "ny": round(ny, 6),
            "weight": round(float(weight), 4),
            "target_id": pt.get("target_id"),
            "target_name": pt.get("target_name"),
            "track_id": pt.get("track_id"),
        })
    return normalized


def merge_multi_camera_points(
    camera_datasets: List[Dict[str, Any]],
) -> List[Dict[str, float]]:
    """
    Merge gaze/attention coordinate datasets from multiple cameras
    into a unified normalized [0.0, 1.0] coordinate space.

    Each camera_dataset dict must have:
      - 'points': list of raw pixel coordinate dicts
      - 'camera_width': int
      - 'camera_height': int

    Returns merged list of normalized points.
    """
    merged = []
    for ds in camera_datasets:
        points = ds.get("points", [])
        cw = ds.get("camera_width", 1280)
        ch = ds.get("camera_height", 720)
        normalized = normalize_camera_coords(points, cw, ch)
        merged.extend(normalized)
    return merged


def compute_density_matrix(
    normalized_points: List[Dict[str, float]],
    grid_width: int = 200,
    grid_height: int = 150,
    sigma: float = 8.0,
    intensity_threshold: float = 0.0,
) -> np.ndarray:
    """
    Compute a 2D Gaussian density matrix from normalized [0,1] points.

    Args:
        normalized_points: list of dicts with 'nx', 'ny', 'weight' in [0,1] space.
        grid_width: output matrix width (pixels).
        grid_height: output matrix height (pixels).
        sigma: Gaussian kernel standard deviation.
        intensity_threshold: minimum weight to include a point (0.0 = no filter).

    Returns:
        np.ndarray of shape (grid_height, grid_width) with float32 density values.
    """
    matrix = np.zeros((grid_height, grid_width), dtype=np.float32)

    for pt in normalized_points:
        w = pt.get("weight", 1.0)
        if w < intensity_threshold:
            continue
        px = int(np.clip(pt["nx"] * (grid_width - 1), 0, grid_width - 1))
        py = int(np.clip(pt["ny"] * (grid_height - 1), 0, grid_height - 1))
        radius = max(int(sigma * 1.5), 3)
        cv2.circle(matrix, (px, py), radius, float(w), -1)

    if np.max(matrix) > 0:
        ksize = int(sigma * 6) | 1  # ensure odd
        matrix = cv2.GaussianBlur(matrix, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)

    return matrix


def density_matrix_to_json(
    matrix: np.ndarray,
    threshold: float = 0.01,
) -> Dict[str, Any]:
    """
    Convert a density matrix to a sparse JSON-friendly representation
    for frontend canvas rendering.

    Returns only cells above the threshold (normalized 0-1).
    """
    max_val = float(np.max(matrix))
    if max_val <= 0:
        return {
            "grid_width": matrix.shape[1],
            "grid_height": matrix.shape[0],
            "max_intensity": 0.0,
            "cells": [],
        }

    norm = matrix / max_val
    ys, xs = np.where(norm > threshold)
    cells = []
    for y, x in zip(ys, xs):
        cells.append({
            "x": int(x),
            "y": int(y),
            "intensity": round(float(norm[y, x]), 4),
        })

    return {
        "grid_width": matrix.shape[1],
        "grid_height": matrix.shape[0],
        "max_intensity": round(max_val, 4),
        "total_cells": len(cells),
        "cells": cells,
    }


def render_heatmap_image(
    matrix: np.ndarray,
    output_path: Path,
    colormap: str = "JET",
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[Path]:
    """
    Render a density matrix as a colormapped PNG image.

    Args:
        matrix: float32 density matrix.
        output_path: destination file path.
        colormap: name from COLORMAP_REGISTRY.
        width: optional resize width.
        height: optional resize height.

    Returns:
        Path to rendered image, or None if matrix is empty.
    """
    max_val = np.max(matrix)
    if max_val <= 0:
        return None

    norm_uint8 = (matrix / max_val * 255.0).astype(np.uint8)

    cv_cmap = COLORMAP_REGISTRY.get(colormap.upper(), cv2.COLORMAP_JET)
    colored = cv2.applyColorMap(norm_uint8, cv_cmap)

    if width and height:
        colored = cv2.resize(colored, (width, height), interpolation=cv2.INTER_LINEAR)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), colored)
    return output_path


def generate_store_heatmap(
    camera_datasets: List[Dict[str, Any]],
    grid_width: int = 200,
    grid_height: int = 150,
    sigma: float = 8.0,
    colormap: str = "JET",
    intensity_threshold: float = 0.0,
    output_image_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    End-to-end store-wide heatmap generation from multiple camera datasets.

    Returns dict with:
      - 'grid': sparse JSON density grid for frontend canvas rendering.
      - 'normalized_points': merged normalized coordinate list.
      - 'image_path': path to rendered PNG (if output_image_path provided).
      - 'metadata': grid dimensions, total points, colormap used.
    """
    # 1. Merge and normalize coordinates
    merged_points = merge_multi_camera_points(camera_datasets)

    # 2. Compute density matrix
    matrix = compute_density_matrix(
        merged_points,
        grid_width=grid_width,
        grid_height=grid_height,
        sigma=sigma,
        intensity_threshold=intensity_threshold,
    )

    # 3. Convert to sparse JSON grid
    grid_json = density_matrix_to_json(matrix)

    # 4. Optionally render image
    image_path = None
    if output_image_path:
        image_path = render_heatmap_image(
            matrix, output_image_path, colormap=colormap,
        )

    return {
        "grid": grid_json,
        "normalized_points": merged_points,
        "image_path": str(image_path) if image_path else None,
        "metadata": {
            "grid_width": grid_width,
            "grid_height": grid_height,
            "total_input_points": len(merged_points),
            "sigma": sigma,
            "colormap": colormap,
            "intensity_threshold": intensity_threshold,
        },
    }
