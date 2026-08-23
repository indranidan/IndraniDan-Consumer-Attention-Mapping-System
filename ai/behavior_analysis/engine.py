"""
Module 6 — Consumer Behavior Intelligence Engine
====================================================
Orchestrates the full Module 6 pipeline: feature extraction → classification →
journey reconstruction → transition matrix → funnel analysis → result assembly.
"""

import logging
from typing import Any, Dict, List, Optional

from ai.behavior_analysis.classifier import BehaviorClassifier
from ai.behavior_analysis.config import BehaviorConfig
from ai.behavior_analysis.feature_extractor import BehaviorFeatureExtractor
from ai.behavior_analysis.funnel_analyzer import FunnelAnalyzer
from ai.behavior_analysis.journey_builder import JourneyBuilder
from ai.behavior_analysis.models import Module6Summary, ShopperArchetype
from ai.behavior_analysis.transition_matrix import TransitionMatrixBuilder


logger = logging.getLogger("module6_engine")


class Module6BehaviorEngine:
    """Orchestrates the complete Module 6 behavioral intelligence pipeline."""

    def __init__(self, config: Optional[BehaviorConfig] = None):
        self.config = config or BehaviorConfig()
        self.feature_extractor = BehaviorFeatureExtractor()
        self.classifier = BehaviorClassifier()
        self.journey_builder = JourneyBuilder()
        self.transition_builder = TransitionMatrixBuilder()
        self.funnel_analyzer = FunnelAnalyzer()

    def analyze(
        self,
        m3_data: Optional[Dict[str, Any]],
        m4_data: Optional[Dict[str, Any]],
        m5_data: Optional[Dict[str, Any]],
        store_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the full Module 6 analysis pipeline.

        Parameters
        ----------
        m3_data : Module 3 movement report (with 'shoppers', 'sessions', 'zones').
        m4_data : Module 4 attention analysis (with 'attention_events', 'shelves').
        m5_data : Module 5 interaction analysis (with 'events', 'product_engagement').

        Returns
        -------
        dict : Complete Module 6 result document.
        """
        sessions = self._extract_sessions(m3_data, m4_data, m5_data)
        logger.info(f"Module 6: Analyzing {len(sessions)} shopper sessions")

        # Filter out transient sessions if end_time and start_time are available
        if sessions:
            valid_sessions = [
                s for s in sessions
                if (s.get("end_time") or s.get("start_time", 0)) - s.get("start_time", 0) >= self.config.min_session_duration_sec
            ]
            if valid_sessions:
                sessions = valid_sessions

        # ── Per-session processing ──────────────────────────────
        shopper_segments = []
        journeys = []
        all_zones = set()
        total_path_eff = 0.0
        total_duration = 0.0
        total_zones = 0

        for session in sessions:
            # Feature extraction
            fv = self.feature_extractor.extract_features(session, m3_data, m4_data, m5_data)

            # Classification
            classification = self.classifier.classify(
                fv, self.config,
                track_id=session.get("tracking_id", 0),
                session_id=session.get("session_id"),
            )
            shopper_segments.append(classification.to_dict())

            # Journey reconstruction
            journey = self.journey_builder.build_journey(session, m3_data, m4_data, m5_data)
            journeys.append(journey)

            # Collect aggregate stats
            total_path_eff += fv.path_efficiency
            total_duration += journey.get("total_duration_sec", 0.0)
            zones = session.get("zones_visited", [])
            total_zones += len(set(zones))
            all_zones.update(zones)

        n = len(sessions) or 1

        # ── Summary ─────────────────────────────────────────────
        summary = self._build_summary(shopper_segments, n, total_path_eff, total_duration, total_zones)

        # ── Zone transition matrix ──────────────────────────────
        zone_names = sorted(all_zones) if all_zones else []
        transitions = self.transition_builder.build_matrix(
            journeys, zone_names, min_sessions=self.config.transition_min_sessions,
        )

        # ── Funnel analysis ─────────────────────────────────────
        funnel = self.funnel_analyzer.compute_funnel(journeys)
        friction_points = self.funnel_analyzer.detect_friction_points(
            journeys, m4_data, m5_data,
            min_gaze_shoppers=self.config.friction_min_gaze_shoppers,
            max_interaction_rate=self.config.friction_max_interaction_rate,
        )

        # ── Product preferences ─────────────────────────────────
        product_preferences = self._compute_product_preferences(m5_data, shopper_segments)

        return {
            "job_id": job_id,
            "store_id": store_id,
            "camera_id": camera_id,
            "summary": summary.to_dict(),
            "shopper_segments": shopper_segments,
            "journeys": [j for j in journeys],
            "zone_transitions": transitions,
            "funnel": funnel,
            "friction_points": friction_points,
            "product_preferences": product_preferences,
        }

    def _extract_sessions(
        self,
        m3_data: Optional[Dict[str, Any]],
        m4_data: Optional[Dict[str, Any]] = None,
        m5_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract shopper sessions from Module 3 data, or reconstruct from M4/M5 tracks if needed."""
        if m3_data:
            sessions = m3_data.get("sessions", [])
            if sessions:
                return sessions

            shoppers = m3_data.get("shoppers", [])
            if shoppers:
                reconstructed = []
                for s in shoppers:
                    tid = s.get("tracking_id") or s.get("track_id") or 1
                    reconstructed.append({
                        "tracking_id": tid,
                        "session_id": f"sess_{tid}",
                        "start_time": s.get("start_time", 0.0),
                        "end_time": s.get("end_time", s.get("start_time", 0.0) + 10.0),
                        "zones_visited": s.get("zones_visited", []),
                        "zone_transitions": s.get("zone_transitions", []),
                        "status": "completed",
                    })
                return reconstructed

        # Fallback: extract distinct track IDs from M4/M5 events if M3 has no explicit session records
        track_ids = set()
        if m4_data:
            for ev in m4_data.get("attention_events", []):
                tid = ev.get("track_id") or ev.get("tracking_id")
                if tid is not None:
                    track_ids.add(tid)
        if m5_data:
            for ev in m5_data.get("events", []):
                tid = ev.get("track_id") or ev.get("tracking_id")
                if tid is not None:
                    track_ids.add(tid)

        if track_ids:
            return [
                {
                    "tracking_id": tid,
                    "session_id": f"sess_{tid}",
                    "start_time": 0.0,
                    "end_time": 15.0,
                    "zones_visited": ["Main Zone"],
                    "zone_transitions": [],
                    "status": "completed",
                }
                for tid in sorted(track_ids)
            ]

        return []

    def _build_summary(
        self,
        segments: List[Dict[str, Any]],
        total: int,
        total_path_eff: float,
        total_duration: float,
        total_zones: int,
    ) -> Module6Summary:
        """Aggregate segment statistics safely."""
        segment_counts: Dict[str, int] = {}
        segment_confidences: Dict[str, List[float]] = {}

        for seg in segments:
            archetype = seg.get("primary_segment", "EXPLORER")
            segment_counts[archetype] = segment_counts.get(archetype, 0) + 1
            if archetype not in segment_confidences:
                segment_confidences[archetype] = []
            segment_confidences[archetype].append(seg.get("confidence", 0.0))

        actual_total = len(segments)
        denom = max(1, actual_total)

        segment_percentages = {k: round(v / denom * 100, 2) for k, v in segment_counts.items()}
        avg_confidence = {
            k: round(sum(v) / len(v), 4) if v else 0.0
            for k, v in segment_confidences.items()
        }

        return Module6Summary(
            total_sessions=actual_total,
            segment_counts=segment_counts,
            segment_percentages=segment_percentages,
            avg_confidence_per_segment=avg_confidence,
            average_journey_duration_sec=round(total_duration / denom, 2),
            average_path_efficiency=round(total_path_eff / denom, 4),
            average_zones_per_shopper=round(total_zones / denom, 2),
        )

    def _compute_product_preferences(
        self,
        m5_data: Optional[Dict[str, Any]],
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compute product preference scores from interaction data."""
        if not m5_data:
            return []

        product_stats: Dict[str, Dict[str, Any]] = {}
        events = m5_data.get("events", [])

        for evt in events:
            product = evt.get("product_name", evt.get("product_id"))
            if not product:
                continue
            if product not in product_stats:
                product_stats[product] = {
                    "product_name": product,
                    "product_id": evt.get("product_id", product),
                    "views": 0, "pickups": 0, "returns": 0,
                    "track_ids": set(),
                }
            evt_type = evt.get("event_type", "")
            if "VIEWED" in evt_type:
                product_stats[product]["views"] += 1
            elif "PICKED_UP" in evt_type:
                product_stats[product]["pickups"] += 1
            elif "RETURNED" in evt_type:
                product_stats[product]["returns"] += 1
            track = evt.get("track_id")
            if track is not None:
                product_stats[product]["track_ids"].add(track)

        # Build segment mapping for dominant segment per product
        track_segment = {}
        for seg in segments:
            track_segment[seg.get("track_id")] = seg.get("primary_segment", "EXPLORER")

        preferences = []
        for name, stats in product_stats.items():
            # Simple preference score: weighted views + pickups
            score = stats["views"] * 1.0 + stats["pickups"] * 3.0 - stats["returns"] * 1.5
            score = max(score, 0.0)

            # Dominant segment among interactors
            seg_counts: Dict[str, int] = {}
            for tid in stats["track_ids"]:
                seg = track_segment.get(tid, "EXPLORER")
                seg_counts[seg] = seg_counts.get(seg, 0) + 1
            dominant = max(seg_counts, key=seg_counts.get) if seg_counts else "EXPLORER"

            preferences.append({
                "product_name": stats["product_name"],
                "product_id": stats["product_id"],
                "preference_score": round(score, 2),
                "views": stats["views"],
                "pickups": stats["pickups"],
                "returns": stats["returns"],
                "unique_interactors": len(stats["track_ids"]),
                "dominant_shopper_segment": dominant,
            })

        return sorted(preferences, key=lambda x: x["preference_score"], reverse=True)
