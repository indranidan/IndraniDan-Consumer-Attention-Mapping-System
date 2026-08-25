"""
Module 7 — Hotspot & Dead-Zone Diagnostic Engine
==================================================
Spatial density clustering to detect retail hotspots, conversion zones,
transit corridors, and dead zones with dwell-to-transit ratio analysis.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("module7.hotspot_engine")

# ── Zone Classification Constants ─────────────────────────────
ZONE_TYPES = {
    "HOTSPOT": "High traffic + High gaze dwell",
    "CONVERSION_ZONE": "High gaze dwell + High product interactions",
    "TRANSIT_CORRIDOR": "High traffic velocity + Low gaze dwell",
    "DEAD_ZONE": "Near-zero attention in accessible area",
}

ZONE_RECOMMENDATIONS = {
    "HOTSPOT": "Maintain current merchandising. Consider premium product placement.",
    "CONVERSION_ZONE": "Optimize product availability and stock levels. Add promotional signage.",
    "TRANSIT_CORRIDOR": "Add impulse purchase displays or promotional endcaps along transit path.",
    "DEAD_ZONE": "Investigate layout blockages. Add signage, lighting, or promotional anchors.",
}

SEVERITY_LEVELS = {
    "HOTSPOT": "LOW",
    "CONVERSION_ZONE": "LOW",
    "TRANSIT_CORRIDOR": "MEDIUM",
    "DEAD_ZONE": "HIGH",
}


def compute_grid_cell_stats(
    attention_points: List[Dict[str, Any]],
    traffic_points: List[Dict[str, Any]],
    interaction_points: List[Dict[str, Any]],
    grid_cols: int = 10,
    grid_rows: int = 8,
) -> List[Dict[str, Any]]:
    """
    Divide the floorplan into a grid and compute per-cell statistics.

    All input points must have 'nx', 'ny' in [0,1] normalized space
    and 'weight' for attention/traffic intensity.

    Returns list of cell stats dicts.
    """
    cells = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            cells.append({
                "row": row,
                "col": col,
                "cx": round((col + 0.5) / grid_cols, 4),
                "cy": round((row + 0.5) / grid_rows, 4),
                "attention_weight": 0.0,
                "attention_count": 0,
                "traffic_weight": 0.0,
                "traffic_count": 0,
                "interaction_count": 0,
            })

    def _assign_to_cell(pt, weight_key, count_key):
        nx = pt.get("nx", pt.get("x", 0))
        ny = pt.get("ny", pt.get("y", 0))
        # If points are not normalized, skip
        if nx > 1.0 or ny > 1.0:
            return
        col = int(np.clip(nx * grid_cols, 0, grid_cols - 1))
        row = int(np.clip(ny * grid_rows, 0, grid_rows - 1))
        idx = row * grid_cols + col
        cells[idx][weight_key] += float(pt.get("weight", 1.0))
        cells[idx][count_key] += 1

    for pt in attention_points:
        _assign_to_cell(pt, "attention_weight", "attention_count")
    for pt in traffic_points:
        _assign_to_cell(pt, "traffic_weight", "traffic_count")
    for pt in interaction_points:
        nx = pt.get("nx", pt.get("x", 0))
        ny = pt.get("ny", pt.get("y", 0))
        if nx > 1.0 or ny > 1.0:
            continue
        col = int(np.clip(nx * grid_cols, 0, grid_cols - 1))
        row = int(np.clip(ny * grid_rows, 0, grid_rows - 1))
        idx = row * grid_cols + col
        cells[idx]["interaction_count"] += 1

    return cells


def classify_zones(
    cells: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Classify grid cells into zone types based on percentile thresholds.

    Returns list of classified zone dicts (only non-trivial cells).
    """
    if not cells:
        return []

    attn_weights = np.array([c["attention_weight"] for c in cells])
    traffic_weights = np.array([c["traffic_weight"] for c in cells])
    interaction_counts = np.array([c["interaction_count"] for c in cells])

    # Percentile thresholds
    attn_p70 = float(np.percentile(attn_weights, 70)) if np.max(attn_weights) > 0 else 0
    traffic_p70 = float(np.percentile(traffic_weights, 70)) if np.max(traffic_weights) > 0 else 0
    traffic_p30 = float(np.percentile(traffic_weights, 30)) if np.max(traffic_weights) > 0 else 0
    interaction_p50 = float(np.percentile(interaction_counts, 50)) if np.max(interaction_counts) > 0 else 0

    classified = []
    for cell in cells:
        attn = cell["attention_weight"]
        traffic = cell["traffic_weight"]
        interactions = cell["interaction_count"]

        # Skip cells with no activity at all
        if attn == 0 and traffic == 0 and interactions == 0:
            continue

        # Dwell-to-transit ratio
        dwell_to_transit = round(attn / max(traffic, 0.01), 3)

        # Classification logic
        if attn >= attn_p70 and traffic >= traffic_p70:
            zone_type = "HOTSPOT"
        elif attn >= attn_p70 and interactions > interaction_p50:
            zone_type = "CONVERSION_ZONE"
        elif traffic >= traffic_p70 and attn < attn_p70 * 0.3:
            zone_type = "TRANSIT_CORRIDOR"
        elif traffic >= traffic_p30 and attn < attn_p70 * 0.1:
            zone_type = "DEAD_ZONE"
        else:
            # Normal zone — skip from diagnostic output
            continue

        classified.append({
            "row": cell["row"],
            "col": cell["col"],
            "center_x": cell["cx"],
            "center_y": cell["cy"],
            "zone_type": zone_type,
            "description": ZONE_TYPES[zone_type],
            "severity": SEVERITY_LEVELS[zone_type],
            "recommendation": ZONE_RECOMMENDATIONS[zone_type],
            "dwell_to_transit_ratio": dwell_to_transit,
            "attention_weight": round(attn, 2),
            "traffic_weight": round(traffic, 2),
            "interaction_count": interactions,
        })

    return classified


def compute_hotspot_diagnostics(
    attention_points: List[Dict[str, Any]],
    traffic_points: List[Dict[str, Any]],
    interaction_points: Optional[List[Dict[str, Any]]] = None,
    grid_cols: int = 10,
    grid_rows: int = 8,
) -> Dict[str, Any]:
    """
    End-to-end hotspot and dead-zone diagnostic analysis.

    Returns:
        dict with 'zones', 'summary', and 'grid_meta'.
    """
    interactions = interaction_points or []

    cells = compute_grid_cell_stats(
        attention_points, traffic_points, interactions,
        grid_cols=grid_cols, grid_rows=grid_rows,
    )

    zones = classify_zones(cells)

    # Build summary
    type_counts = {}
    for z in zones:
        t = z["zone_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    avg_dtr = 0.0
    if zones:
        avg_dtr = round(float(np.mean([z["dwell_to_transit_ratio"] for z in zones])), 3)

    return {
        "zones": zones,
        "summary": {
            "total_diagnostic_zones": len(zones),
            "hotspot_count": type_counts.get("HOTSPOT", 0),
            "conversion_zone_count": type_counts.get("CONVERSION_ZONE", 0),
            "transit_corridor_count": type_counts.get("TRANSIT_CORRIDOR", 0),
            "dead_zone_count": type_counts.get("DEAD_ZONE", 0),
            "avg_dwell_to_transit_ratio": avg_dtr,
        },
        "grid_meta": {
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "total_cells": len(cells),
        },
    }
