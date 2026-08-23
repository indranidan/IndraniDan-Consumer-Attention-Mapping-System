"""
Module 6 — Journey Builder
=============================
Reconstructs chronological stage-progression timelines per shopper session.
"""

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger("journey_builder")


class JourneyBuilder:
    """Builds end-to-end journey timelines from Module 3/4/5 data."""

    STAGE_ENTRY = "ENTRY"
    STAGE_ZONE_VISIT = "ZONE_VISIT"
    STAGE_SHELF_GAZE = "SHELF_GAZE"
    STAGE_PRODUCT_INTERACTION = "PRODUCT_INTERACTION"
    STAGE_EXIT = "EXIT"

    def build_journey(
        self,
        session: Dict[str, Any],
        m3_data: Optional[Dict[str, Any]],
        m4_data: Optional[Dict[str, Any]],
        m5_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build a journey timeline for a single shopper session.

        Returns
        -------
        dict with keys: session_id, track_id, status, timeline (list of stage events),
        total_duration_sec.
        """
        track_id = session.get("tracking_id")
        session_id = session.get("session_id", f"sess_{track_id}")
        raw_start = session.get("start_time")
        start_time = float(raw_start) if raw_start is not None else 0.0
        raw_end = session.get("end_time")
        end_time = float(raw_end) if raw_end is not None else None
        status = session.get("status", "active")

        timeline: List[Dict[str, Any]] = []

        # ── ENTRY ───────────────────────────────────────────────
        raw_entry = session.get("entry_time")
        entry_time = float(raw_entry) if raw_entry is not None else start_time
        entry_zone = None
        zones_visited = session.get("zones_visited", [])
        if zones_visited:
            entry_zone = zones_visited[0]
        timeline.append({
            "timestamp": round(entry_time, 3),
            "stage": self.STAGE_ENTRY,
            "zone": entry_zone,
            "duration": 0.0,
        })

        # ── ZONE VISITS from transitions ────────────────────────
        transitions = session.get("zone_transitions", [])
        for t in transitions:
            zone_name = t.get("zone", t.get("to_zone", "Unknown"))
            raw_zt = t.get("enter_time", t.get("timestamp", entry_time))
            zone_time = float(raw_zt) if raw_zt is not None else entry_time
            zone_dur = float(t.get("duration", t.get("dwell_time", 0.0)) or 0.0)
            timeline.append({
                "timestamp": round(zone_time, 3),
                "stage": self.STAGE_ZONE_VISIT,
                "zone": zone_name,
                "duration": round(zone_dur, 3),
            })

        # ── SHELF GAZE from M4 attention events ────────────────
        if m4_data:
            for evt in m4_data.get("attention_events", []):
                evt_track = evt.get("track_id", evt.get("tracking_id"))
                if evt_track != track_id:
                    continue
                raw_st = evt.get("start_time", evt.get("timestamp", 0))
                gaze_time = float(raw_st) if raw_st is not None else entry_time
                gaze_dur = float(evt.get("duration_seconds", evt.get("duration", 0.0)) or 0.0)
                timeline.append({
                    "timestamp": round(gaze_time, 3),
                    "stage": self.STAGE_SHELF_GAZE,
                    "shelf": evt.get("target_id", evt.get("shelf_id", "Unknown")),
                    "duration": round(gaze_dur, 3),
                })

        # ── PRODUCT INTERACTIONS from M5 events ────────────────
        if m5_data:
            for evt in m5_data.get("events", []):
                if evt.get("track_id") != track_id:
                    continue
                raw_pt = evt.get("timestamp", evt.get("start_time", 0))
                prod_time = float(raw_pt) if raw_pt is not None else entry_time
                prod_dur = float(evt.get("duration_seconds", 0.0) or 0.0)
                timeline.append({
                    "timestamp": round(prod_time, 3),
                    "stage": self.STAGE_PRODUCT_INTERACTION,
                    "product": evt.get("product_name", evt.get("product_id", "Unknown")),
                    "event_type": evt.get("event_type", "UNKNOWN"),
                    "duration": round(prod_dur, 3),
                })

        # ── EXIT ────────────────────────────────────────────────
        is_complete = end_time is not None and status in ("completed", "exited", "track_lost")
        if is_complete and end_time is not None:
            exit_zone = zones_visited[-1] if zones_visited else None
            timeline.append({
                "timestamp": round(end_time, 3),
                "stage": self.STAGE_EXIT,
                "zone": exit_zone,
                "duration": 0.0,
            })
            journey_status = "complete"
        else:
            journey_status = "incomplete"

        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x.get("timestamp", 0))

        total_duration = (end_time - start_time) if end_time is not None else 0.0


        return {
            "session_id": session_id,
            "track_id": track_id,
            "status": journey_status,
            "timeline": timeline,
            "total_duration_sec": round(max(total_duration, 0.0), 3),
        }
