"""
Module 7 — Customer Traffic & Trajectory Flow Density
======================================================
Computes path density lines, movement velocity vectors, and aisle
flow direction from Module 3 tracking trajectories.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("module7.traffic_heatmap")


def compute_path_density(
    trajectories: List[Dict[str, Any]],
    grid_width: int = 200,
    grid_height: int = 150,
    frame_width: int = 1280,
    frame_height: int = 720,
    sigma: float = 5.0,
) -> Dict[str, Any]:
    """
    Compute a 2D path density matrix from shopper tracking trajectories.

    Args:
        trajectories: list of shopper trajectory dicts, each with a 'path'
                       field containing list of {'x', 'y', 'frame'} positions.
        grid_width: output density grid width.
        grid_height: output density grid height.
        frame_width: original camera frame width.
        frame_height: original camera frame height.
        sigma: Gaussian blur standard deviation.

    Returns:
        dict with 'density_matrix' (as list of lists), 'metadata', and 'flow_vectors'.
    """
    import cv2

    matrix = np.zeros((grid_height, grid_width), dtype=np.float32)
    flow_vectors = []

    for traj in trajectories:
        path = traj.get("path", [])
        if isinstance(path, dict):
            # Handle paths stored as {track_id: [{x,y,...}]}
            path = list(path.values())[0] if path else []
        if not isinstance(path, list) or len(path) < 2:
            continue

        prev_pt = None
        for pt in path:
            x = pt.get("x", pt.get("cx", 0))
            y = pt.get("y", pt.get("cy", 0))

            # Map to grid coordinates
            gx = int(np.clip(x / frame_width * (grid_width - 1), 0, grid_width - 1))
            gy = int(np.clip(y / frame_height * (grid_height - 1), 0, grid_height - 1))

            # Accumulate density
            matrix[gy, gx] += 1.0

            # Compute velocity vector between consecutive points
            if prev_pt is not None:
                px, py = prev_pt
                dx = gx - px
                dy = gy - py
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0.5:
                    flow_vectors.append({
                        "x": gx,
                        "y": gy,
                        "dx": round(dx / dist, 4),
                        "dy": round(dy / dist, 4),
                        "speed": round(dist, 2),
                    })
            prev_pt = (gx, gy)

    # Gaussian blur for smooth density
    if np.max(matrix) > 0:
        ksize = int(sigma * 6) | 1
        matrix = cv2.GaussianBlur(matrix, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)

    # Downsample flow vectors to representative set (max 500)
    if len(flow_vectors) > 500:
        indices = np.linspace(0, len(flow_vectors) - 1, 500, dtype=int)
        flow_vectors = [flow_vectors[i] for i in indices]

    max_val = float(np.max(matrix))

    return {
        "density_matrix": matrix,
        "flow_vectors": flow_vectors,
        "metadata": {
            "grid_width": grid_width,
            "grid_height": grid_height,
            "total_trajectories": len(trajectories),
            "total_flow_vectors": len(flow_vectors),
            "max_density": round(max_val, 4),
            "sigma": sigma,
        },
    }


def density_to_sparse_json(
    matrix: np.ndarray,
    threshold: float = 0.01,
) -> List[Dict[str, Any]]:
    """
    Convert density matrix to sparse JSON cells for frontend rendering.
    """
    max_val = float(np.max(matrix))
    if max_val <= 0:
        return []

    norm = matrix / max_val
    ys, xs = np.where(norm > threshold)
    cells = []
    for y, x in zip(ys, xs):
        cells.append({
            "x": int(x),
            "y": int(y),
            "intensity": round(float(norm[y, x]), 4),
        })
    return cells


def compute_traffic_flow_summary(
    trajectories: List[Dict[str, Any]],
    frame_width: int = 1280,
    frame_height: int = 720,
) -> Dict[str, Any]:
    """
    Compute summary traffic flow statistics.

    Returns:
        dict with avg_speed, dominant_direction, path_count, avg_path_length.
    """
    speeds = []
    directions = {"LEFT": 0, "RIGHT": 0, "UP": 0, "DOWN": 0}
    path_lengths = []

    for traj in trajectories:
        path = traj.get("path", [])
        if isinstance(path, dict):
            path = list(path.values())[0] if path else []
        if not isinstance(path, list) or len(path) < 2:
            continue

        total_dist = 0.0
        for i in range(1, len(path)):
            x1 = path[i - 1].get("x", path[i - 1].get("cx", 0))
            y1 = path[i - 1].get("y", path[i - 1].get("cy", 0))
            x2 = path[i].get("x", path[i].get("cx", 0))
            y2 = path[i].get("y", path[i].get("cy", 0))

            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy)
            total_dist += dist

            if abs(dx) > abs(dy):
                directions["RIGHT" if dx > 0 else "LEFT"] += 1
            else:
                directions["DOWN" if dy > 0 else "UP"] += 1

        path_lengths.append(total_dist)
        # Speed approximation: distance per frame
        frame_count = len(path)
        if frame_count > 1:
            speeds.append(total_dist / frame_count)

    dominant_direction = max(directions.items(), key=lambda x: x[1])[0] if any(directions.values()) else "UNKNOWN"

    return {
        "total_paths": len(trajectories),
        "avg_speed": round(float(np.mean(speeds)), 2) if speeds else 0.0,
        "avg_path_length": round(float(np.mean(path_lengths)), 2) if path_lengths else 0.0,
        "dominant_direction": dominant_direction,
        "direction_counts": directions,
    }
