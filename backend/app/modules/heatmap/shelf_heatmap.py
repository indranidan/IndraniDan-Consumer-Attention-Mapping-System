"""
Module 7 — Shelf Vertical & Horizontal Planogram Heatmap
==========================================================
Computes vertical tier gaze fixation distributions (Top, Eye-Level,
Reach, Bottom) and horizontal planogram attention spread for individual
shelf fixtures.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("module7.shelf_heatmap")

# ── Retail Shelf Vertical Tier Definitions ────────────────────
# Standard FMCG retail merchandising height boundaries (normalized 0-1)
TIER_DEFINITIONS = {
    "TOP_SHELF": {"min_y": 0.0, "max_y": 0.25, "label": "Top Shelf"},
    "EYE_LEVEL": {"min_y": 0.25, "max_y": 0.50, "label": "Eye Level"},
    "REACH_LEVEL": {"min_y": 0.50, "max_y": 0.75, "label": "Reach Level"},
    "BOTTOM_SHELF": {"min_y": 0.75, "max_y": 1.0, "label": "Bottom Shelf"},
}


def compute_shelf_vertical_tiers(
    gaze_points: List[Dict[str, Any]],
    shelf_bbox: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compute vertical tier gaze fixation distributions for a shelf.

    Args:
        gaze_points: list of dicts with at minimum 'y' (pixel) and 'weight' (duration).
        shelf_bbox: optional {'x': float, 'y': float, 'width': float, 'height': float}
                    bounding box of the shelf in camera coordinates. If provided,
                    gaze_points y-values are normalized relative to this bbox.

    Returns:
        dict with:
          - 'tiers': dict of tier_name -> {count, total_weight, percentage, avg_weight}
          - 'eye_level_concentration': float (percentage of total weight at eye level)
          - 'vertical_distribution': list of {tier, label, percentage, engagement_score}
          - 'total_gaze_events': int
          - 'total_weight': float
    """
    if not gaze_points:
        return _empty_tier_result()

    # Normalize y coordinates to [0.0, 1.0] relative to shelf bbox or frame
    bbox_y = shelf_bbox.get("y", 0) if shelf_bbox else 0
    bbox_h = shelf_bbox.get("height", 1) if shelf_bbox else 1
    if bbox_h <= 0:
        bbox_h = 1

    tier_stats = {}
    for tier_name, bounds in TIER_DEFINITIONS.items():
        tier_stats[tier_name] = {
            "count": 0,
            "total_weight": 0.0,
            "label": bounds["label"],
        }

    total_weight = 0.0
    for pt in gaze_points:
        raw_y = pt.get("y", 0)
        weight = float(pt.get("weight", 1.0))

        # Normalize y relative to shelf bounding box
        norm_y = float(np.clip((raw_y - bbox_y) / bbox_h, 0.0, 1.0))

        total_weight += weight

        for tier_name, bounds in TIER_DEFINITIONS.items():
            if bounds["min_y"] <= norm_y < bounds["max_y"]:
                tier_stats[tier_name]["count"] += 1
                tier_stats[tier_name]["total_weight"] += weight
                break

    # Calculate percentages and engagement scores
    vertical_distribution = []
    for tier_name, stats in tier_stats.items():
        pct = (stats["total_weight"] / total_weight * 100) if total_weight > 0 else 0.0
        avg_w = stats["total_weight"] / max(1, stats["count"])
        stats["percentage"] = round(pct, 1)
        stats["avg_weight"] = round(avg_w, 3)

        # Engagement score: normalize tier performance relative to even distribution (25%)
        engagement_score = min(100.0, (pct / 25.0) * 50.0 + avg_w * 10.0) if pct > 0 else 0.0
        vertical_distribution.append({
            "tier": tier_name,
            "label": stats["label"],
            "percentage": round(pct, 1),
            "engagement_score": round(engagement_score, 1),
            "gaze_events": stats["count"],
            "total_duration": round(stats["total_weight"], 2),
        })

    eye_level_weight = tier_stats["EYE_LEVEL"]["total_weight"]
    eye_level_concentration = (eye_level_weight / total_weight * 100) if total_weight > 0 else 0.0

    return {
        "tiers": tier_stats,
        "eye_level_concentration": round(eye_level_concentration, 1),
        "vertical_distribution": vertical_distribution,
        "total_gaze_events": len(gaze_points),
        "total_weight": round(total_weight, 2),
    }


def compute_shelf_horizontal_distribution(
    gaze_points: List[Dict[str, Any]],
    shelf_bbox: Optional[Dict[str, float]] = None,
    num_bins: int = 10,
) -> Dict[str, Any]:
    """
    Compute horizontal gaze distribution across a shelf's width.

    Divides the shelf into `num_bins` equal horizontal segments
    and calculates attention weight in each.
    """
    if not gaze_points:
        return {
            "bins": [],
            "num_bins": num_bins,
            "total_gaze_events": 0,
            "peak_bin_index": None,
        }

    bbox_x = shelf_bbox.get("x", 0) if shelf_bbox else 0
    bbox_w = shelf_bbox.get("width", 1) if shelf_bbox else 1
    if bbox_w <= 0:
        bbox_w = 1

    bin_weights = [0.0] * num_bins
    bin_counts = [0] * num_bins

    for pt in gaze_points:
        raw_x = pt.get("x", 0)
        weight = float(pt.get("weight", 1.0))
        norm_x = float(np.clip((raw_x - bbox_x) / bbox_w, 0.0, 0.9999))
        bin_idx = int(norm_x * num_bins)
        bin_weights[bin_idx] += weight
        bin_counts[bin_idx] += 1

    max_weight = max(bin_weights) if bin_weights else 0
    bins = []
    for i in range(num_bins):
        pct = (bin_weights[i] / sum(bin_weights) * 100) if sum(bin_weights) > 0 else 0
        bins.append({
            "bin_index": i,
            "start_pct": round(i / num_bins * 100, 1),
            "end_pct": round((i + 1) / num_bins * 100, 1),
            "gaze_events": bin_counts[i],
            "total_weight": round(bin_weights[i], 2),
            "percentage": round(pct, 1),
            "normalized_intensity": round(bin_weights[i] / max_weight, 4) if max_weight > 0 else 0,
        })

    peak_idx = int(np.argmax(bin_weights)) if max_weight > 0 else None

    return {
        "bins": bins,
        "num_bins": num_bins,
        "total_gaze_events": len(gaze_points),
        "peak_bin_index": peak_idx,
    }


def compute_full_shelf_heatmap(
    gaze_points: List[Dict[str, Any]],
    shelf_id: str,
    shelf_name: str,
    shelf_bbox: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compute full vertical + horizontal shelf heatmap analysis.
    """
    vertical = compute_shelf_vertical_tiers(gaze_points, shelf_bbox)
    horizontal = compute_shelf_horizontal_distribution(gaze_points, shelf_bbox)

    return {
        "shelf_id": shelf_id,
        "shelf_name": shelf_name,
        "vertical_analysis": vertical,
        "horizontal_analysis": horizontal,
        "total_gaze_events": len(gaze_points),
        "summary": {
            "eye_level_concentration": vertical["eye_level_concentration"],
            "dominant_tier": _get_dominant_tier(vertical),
            "peak_horizontal_bin": horizontal.get("peak_bin_index"),
        },
    }


def _get_dominant_tier(vertical_result: Dict[str, Any]) -> str:
    """Return the tier name with the highest total weight."""
    tiers = vertical_result.get("tiers", {})
    if not tiers:
        return "UNKNOWN"
    return max(tiers.items(), key=lambda t: t[1].get("total_weight", 0))[0]


def _empty_tier_result() -> Dict[str, Any]:
    """Return an empty tier result structure."""
    tier_stats = {}
    vertical_distribution = []
    for tier_name, bounds in TIER_DEFINITIONS.items():
        tier_stats[tier_name] = {
            "count": 0,
            "total_weight": 0.0,
            "percentage": 0.0,
            "avg_weight": 0.0,
            "label": bounds["label"],
        }
        vertical_distribution.append({
            "tier": tier_name,
            "label": bounds["label"],
            "percentage": 0.0,
            "engagement_score": 0.0,
            "gaze_events": 0,
            "total_duration": 0.0,
        })

    return {
        "tiers": tier_stats,
        "eye_level_concentration": 0.0,
        "vertical_distribution": vertical_distribution,
        "total_gaze_events": 0,
        "total_weight": 0.0,
    }
