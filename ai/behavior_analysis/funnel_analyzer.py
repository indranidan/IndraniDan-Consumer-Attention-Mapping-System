"""
Module 6 — Funnel Analyzer
==============================
Computes shopper funnel conversion rates and detects friction points.
"""

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger("funnel_analyzer")


class FunnelAnalyzer:
    """Computes funnel metrics and identifies friction points."""

    FUNNEL_STAGES = ["ENTRY", "ZONE_VISIT", "SHELF_GAZE", "PRODUCT_INTERACTION", "EXIT"]

    def compute_funnel(self, journeys: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute per-stage shopper counts, conversion rates, and dropoff.

        Returns
        -------
        dict with 'stages' (list of stage metrics), 'total_shoppers'.
        """
        total = len(journeys)
        stage_counts = {s: 0 for s in self.FUNNEL_STAGES}

        for journey in journeys:
            stages_seen = set()
            for evt in journey.get("timeline", []):
                stage = evt.get("stage")
                if stage in stage_counts:
                    stages_seen.add(stage)
            for s in stages_seen:
                stage_counts[s] += 1

        stages = []
        for i, stage in enumerate(self.FUNNEL_STAGES):
            count = stage_counts[stage]
            prev_count = stage_counts[self.FUNNEL_STAGES[i - 1]] if i > 0 else total
            conversion = (count / prev_count * 100) if prev_count > 0 else 0.0
            dropoff = prev_count - count if i > 0 else 0
            dropoff_pct = (dropoff / prev_count * 100) if prev_count > 0 else 0.0

            stages.append({
                "stage": stage,
                "shoppers": count,
                "conversion_rate_pct": round(conversion, 2),
                "dropoff": dropoff,
                "dropoff_pct": round(dropoff_pct, 2),
            })

        return {
            "stages": stages,
            "total_shoppers": total,
        }

    def detect_friction_points(
        self,
        journeys: List[Dict[str, Any]],
        m4_data: Optional[Dict[str, Any]],
        m5_data: Optional[Dict[str, Any]],
        min_gaze_shoppers: int = 5,
        max_interaction_rate: float = 0.20,
    ) -> List[Dict[str, Any]]:
        """
        Identify shelves with high gaze attention but low product interaction conversion.

        A friction point is a shelf that received gaze from ≥min_gaze_shoppers
        but fewer than max_interaction_rate of those shoppers interacted.
        """
        if not m4_data:
            return []

        # Count unique shoppers gazing at each shelf
        shelf_gazers: Dict[str, set] = {}
        for evt in m4_data.get("attention_events", []):
            shelf = evt.get("target_id", evt.get("shelf_id"))
            track = evt.get("track_id", evt.get("tracking_id"))
            if shelf and track is not None:
                if shelf not in shelf_gazers:
                    shelf_gazers[shelf] = set()
                shelf_gazers[shelf].add(track)

        # Count unique shoppers interacting at each shelf
        shelf_interactors: Dict[str, set] = {}
        if m5_data:
            for evt in m5_data.get("events", []):
                shelf = evt.get("shelf_id")
                track = evt.get("track_id")
                evt_type = evt.get("event_type", "")
                if shelf and track is not None and "PICKED_UP" in evt_type:
                    if shelf not in shelf_interactors:
                        shelf_interactors[shelf] = set()
                    shelf_interactors[shelf].add(track)

        friction_points = []
        for shelf, gazers in shelf_gazers.items():
            gaze_count = len(gazers)
            if gaze_count < min_gaze_shoppers:
                continue
            interact_count = len(shelf_interactors.get(shelf, set()))
            interaction_rate = interact_count / gaze_count if gaze_count > 0 else 0.0

            if interaction_rate < max_interaction_rate:
                friction_points.append({
                    "shelf_id": shelf,
                    "gaze_shoppers": gaze_count,
                    "interaction_shoppers": interact_count,
                    "interaction_rate": round(interaction_rate, 4),
                    "is_friction_point": True,
                })

        return sorted(friction_points, key=lambda x: x["interaction_rate"])
