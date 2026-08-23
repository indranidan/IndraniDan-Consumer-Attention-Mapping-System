"""
Module 6 — Behavioral Feature Extractor
=========================================
Computes per-session behavioral feature vectors from Module 3 tracking,
Module 4 attention, and Module 5 interaction data.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from ai.behavior_analysis.models import BehaviorFeatureVector


logger = logging.getLogger("behavior_feature_extractor")


class BehaviorFeatureExtractor:
    """Extracts behavioral features from upstream module outputs for a single session."""

    def extract_features(
        self,
        session: Dict[str, Any],
        m3_data: Optional[Dict[str, Any]],
        m4_data: Optional[Dict[str, Any]],
        m5_data: Optional[Dict[str, Any]],
    ) -> BehaviorFeatureVector:
        """
        Compute the behavioral feature vector for one shopper session.

        Parameters
        ----------
        session : dict
            A shopper session dict with keys like 'tracking_id', 'zones_visited',
            'zone_transitions', 'start_time', 'end_time', 'journey', 'status'.
        m3_data : dict or None
            Module 3 movement report containing 'shoppers' with path coordinates.
        m4_data : dict or None
            Module 4 attention analysis with 'attention_events' or 'shelves'.
        m5_data : dict or None
            Module 5 interaction analysis with 'events', 'product_engagement'.

        Returns
        -------
        BehaviorFeatureVector
        """
        has_reduced = False

        # ── Path efficiency ─────────────────────────────────────
        path_efficiency = self._compute_path_efficiency(session, m3_data)

        # ── Dwell-to-transit ratio ──────────────────────────────
        dwell_to_transit = self._compute_dwell_to_transit(session)

        # ── Zone breadth ────────────────────────────────────────
        zones_visited = session.get("zones_visited", [])
        zone_breadth = len(set(zones_visited)) if zones_visited else 0

        # ── Attention-derived features ──────────────────────────
        if m4_data:
            gaze_alternation = self._compute_gaze_alternation(session, m4_data)
        else:
            gaze_alternation = 0.0
            has_reduced = True

        # ── Interaction-derived features ────────────────────────
        if m5_data:
            pickup_to_return = self._compute_pickup_to_return(session, m5_data)
            brand_concentration = self._compute_brand_concentration(session, m5_data)
            promo_deviation = self._compute_promo_deviations(session, m5_data)
        else:
            pickup_to_return = 0.0
            brand_concentration = 0.0
            promo_deviation = 0
            has_reduced = True

        return BehaviorFeatureVector(
            path_efficiency=path_efficiency,
            dwell_to_transit_ratio=dwell_to_transit,
            zone_breadth=zone_breadth,
            gaze_alternation_rate=gaze_alternation,
            pickup_to_return_ratio=pickup_to_return,
            brand_concentration=brand_concentration,
            promo_deviation_count=promo_deviation,
            has_reduced_confidence=has_reduced,
        )

    # ── Private helpers ─────────────────────────────────────────

    def _compute_path_efficiency(
        self, session: Dict[str, Any], m3_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        Path efficiency = Euclidean(entry, exit) / total_path_distance.
        Returns 0.5 if insufficient path data.
        """
        track_id = session.get("tracking_id") or session.get("track_id")
        path_points: List[Any] = []

        # 1. Try to get path from m3 paths dict
        if m3_data and "paths" in m3_data and isinstance(m3_data["paths"], dict):
            path_points = m3_data["paths"].get(str(track_id)) or m3_data["paths"].get(track_id) or []

        # 2. Try to get path from m3 shopper list or dict
        if not path_points and m3_data:
            shoppers = m3_data.get("shoppers", [])
            if isinstance(shoppers, list):
                for shopper in shoppers:
                    if isinstance(shopper, dict):
                        if shopper.get("tracking_id") == track_id or shopper.get("track_id") == track_id:
                            path_points = shopper.get("path", shopper.get("full_path", []))
                            break
            elif isinstance(shoppers, dict):
                path_points = shoppers.get(str(track_id)) or shoppers.get(track_id) or []

        # 3. Fallback: try session embedded path
        if not path_points and "path" in session and isinstance(session["path"], list):
            path_points = session["path"]


        # Fallback: try session journey for approximate path
        if not path_points:
            journey = session.get("journey", [])
            if len(journey) >= 2:
                # Cannot compute precise path efficiency without coordinates
                return 0.5
            return 0.5

        if len(path_points) < 2:
            return 0.5

        def _get_coord(pt):
            if isinstance(pt, dict):
                return float(pt.get("x", 0.0)), float(pt.get("y", 0.0))
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                return float(pt[0]), float(pt[1])
            return 0.0, 0.0

        # Compute total walking distance
        total_dist = 0.0
        for i in range(1, len(path_points)):
            x1, y1 = _get_coord(path_points[i - 1])
            x2, y2 = _get_coord(path_points[i])
            dx = x2 - x1
            dy = y2 - y1
            total_dist += math.sqrt(dx * dx + dy * dy)

        if total_dist < 1.0:
            return 1.0

        # Euclidean direct distance entry → exit
        x_first, y_first = _get_coord(path_points[0])
        x_last, y_last = _get_coord(path_points[-1])
        dx = x_last - x_first
        dy = y_last - y_first
        direct_dist = math.sqrt(dx * dx + dy * dy)

        return min(direct_dist / total_dist, 1.0)


    def _compute_dwell_to_transit(self, session: Dict[str, Any]) -> float:
        """Ratio of dwell time to total session duration."""
        start = session.get("start_time", 0.0)
        end = session.get("end_time")
        if end is None:
            end = start

        total_duration = max(end - start, 0.001)

        # Sum zone dwell durations from transitions
        dwell_time = 0.0
        transitions = session.get("zone_transitions", [])
        for t in transitions:
            dwell_time += t.get("duration", t.get("dwell_time", 0.0))

        if dwell_time <= 0.0:
            # Fallback: estimate from journey events
            journey = session.get("journey", [])
            for evt in journey:
                d = evt.get("duration", 0.0)
                if d > 0:
                    dwell_time += d

        return min(dwell_time / total_duration, 1.0) if total_duration > 0 else 0.0

    def _compute_gaze_alternation(
        self, session: Dict[str, Any], m4_data: Dict[str, Any]
    ) -> float:
        """
        Gaze alternation rate = number of target switches / total shelf dwell time.
        """
        track_id = session.get("tracking_id")
        events = m4_data.get("attention_events", [])

        # Filter attention events for this track
        track_events = [
            e for e in events
            if e.get("track_id") == track_id or e.get("tracking_id") == track_id
        ]

        if len(track_events) < 2:
            return 0.0

        # Count target switches
        switches = 0
        total_duration = 0.0
        prev_target = None
        for evt in sorted(track_events, key=lambda x: x.get("start_time", x.get("timestamp", 0))):
            target = evt.get("target_id", evt.get("shelf_id"))
            duration = evt.get("duration_seconds", evt.get("duration", 0.0))
            total_duration += duration
            if prev_target is not None and target != prev_target:
                switches += 1
            prev_target = target

        if total_duration <= 0:
            return float(switches)

        return switches / total_duration

    def _compute_pickup_to_return(
        self, session: Dict[str, Any], m5_data: Dict[str, Any]
    ) -> float:
        """Pickup-to-return ratio = pickups / (returns + 1)."""
        track_id = session.get("tracking_id")
        events = m5_data.get("events", [])

        pickups = 0
        returns = 0
        for evt in events:
            evt_track = evt.get("track_id")
            if evt_track != track_id:
                continue
            evt_type = evt.get("event_type", "")
            if "PICKED_UP" in evt_type:
                pickups += 1
            elif "RETURNED" in evt_type:
                returns += 1

        return pickups / (returns + 1)

    def _compute_brand_concentration(
        self, session: Dict[str, Any], m5_data: Dict[str, Any]
    ) -> float:
        """Max brand interaction share: max(interactions(brand_b) / total_interactions)."""
        track_id = session.get("tracking_id")
        events = m5_data.get("events", [])

        brand_counts: Dict[str, int] = {}
        total = 0
        for evt in events:
            if evt.get("track_id") != track_id:
                continue
            product = evt.get("product_name", evt.get("product_id", "unknown"))
            if product:
                brand_counts[product] = brand_counts.get(product, 0) + 1
                total += 1

        if total == 0:
            return 0.0

        max_count = max(brand_counts.values())
        return max_count / total

    def _compute_promo_deviations(
        self, session: Dict[str, Any], m5_data: Dict[str, Any]
    ) -> int:
        """Count path deviations toward promotional zones (heuristic)."""
        # Look for zone transitions to zones with 'promo', 'endcap', or 'display' in name
        transitions = session.get("zone_transitions", [])
        promo_count = 0
        for t in transitions:
            zone_name = str(t.get("zone", t.get("to_zone", ""))).lower()
            if any(keyword in zone_name for keyword in ("promo", "endcap", "display", "checkout")):
                promo_count += 1
        return promo_count
