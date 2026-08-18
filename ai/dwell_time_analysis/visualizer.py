"""
Dwell-Time Analysis — Visualizer
===================================
Extends Phase 3 MovementVisualizer with dwell-time overlays (Phase 4.15, 4.16).
Displays live dwell duration inside bounding boxes and HUD.
"""

from typing import Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.movement_analysis.movement_visualizer import MovementVisualizer, _get_track_color
from ai.person_tracking.tracker import TrackData

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.55
_FONT_THICKNESS = 2
_HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
_HUD_SCALE = 0.45
_HUD_COLOR = (0, 255, 255)
_HUD_THICKNESS = 1


class DwellVisualizer(MovementVisualizer):
    """Handles visual annotation of tracks with live dwell time and extended HUD for Phase 4."""

    def draw_track_with_dwell(
        self,
        frame: np.ndarray,
        track: TrackData,
        zone_names: List[str],
        active_dwell_times: Dict[str, float],
    ) -> np.ndarray:
        """
        Draw bounding box with tracking ID, confidence, current zone, and current live dwell time.

        Example display:
            Person 7 | 0.87
            Zone: Beverage Section (32.4s)
        """
        color = _get_track_color(track.track_id)
        x1, y1, x2, y2 = track.bbox

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Build zone label with live dwell time
        if zone_names and active_dwell_times:
            zone_parts = []
            for zid in active_dwell_times:
                dt = active_dwell_times[zid]
                z_name = zone_names[0] if len(zone_names) == 1 else zid
                zone_parts.append(f"{z_name} ({dt:.1f}s)")
            zone_str = ", ".join(zone_parts)
        elif zone_names:
            zone_str = ", ".join(zone_names)
        else:
            zone_str = "—"

        label = f"Person {track.track_id} | {track.confidence:.2f}"
        zone_label = f"Zone: {zone_str}"

        # Calculate text background dimensions
        (tw1, th1), bl1 = cv2.getTextSize(label, _FONT, _FONT_SCALE, _FONT_THICKNESS)
        (tw2, th2), bl2 = cv2.getTextSize(zone_label, _FONT, 0.45, 1)
        max_tw = max(tw1, tw2)

        bg_height = th1 + th2 + bl1 + 10
        cv2.rectangle(frame, (x1, y1 - bg_height), (x1 + max_tw + 8, y1), color, -1)

        cv2.putText(frame, label, (x1 + 2, y1 - th2 - bl2 - 6), _FONT, _FONT_SCALE, (0, 0, 0), _FONT_THICKNESS)
        cv2.putText(frame, zone_label, (x1 + 2, y1 - 4), _FONT, 0.45, (0, 0, 0), 1)

        return frame

    def draw_dwell_hud(
        self,
        frame: np.ndarray,
        frame_number: int,
        active_shoppers: int,
        active_zone_visits: int,
        active_dwell_info: Dict[str, float],
        fps: float,
        inference_ms: float,
        tracking_ms: float,
    ) -> np.ndarray:
        """
        Draw extended HUD showing frame, active count, active visits, and per-zone active dwell times.
        """
        lines = [
            f"Frame: {frame_number}",
            f"Active Shoppers: {active_shoppers} | Active Visits: {active_zone_visits}",
            f"YOLO: {inference_ms:.1f}ms | Tracker: {tracking_ms:.1f}ms | FPS: {fps:.1f}",
        ]

        # Add active dwell lines per zone
        for zone_name, avg_dt in active_dwell_info.items():
            lines.append(f"  {zone_name} active dwell: {avg_dt:.1f}s")

        y = 25
        for line in lines:
            cv2.putText(frame, line, (11, y + 1), _HUD_FONT, _HUD_SCALE, (0, 0, 0), _HUD_THICKNESS + 1)
            cv2.putText(frame, line, (10, y), _HUD_FONT, _HUD_SCALE, _HUD_COLOR, _HUD_THICKNESS)
            y += 18

        return frame
