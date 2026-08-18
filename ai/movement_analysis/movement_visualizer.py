"""
Movement Analysis — Movement Visualizer
==========================================
Extends Phase 2 video annotation with zone boundaries, entry/exit regions,
movement paths, zone labels on tracks, and an expanded HUD showing
zone occupancy and entry/exit counts.
"""

from typing import Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.movement_analysis.path_tracker import ShopperPath
from ai.movement_analysis.zone_manager import ZoneDefinition, ZoneManager
from ai.person_tracking.tracker import TrackData


# Distinct color palette for tracking IDs (BGR format) — reuse from Phase 2
_TRACK_COLORS = [
    (0, 255, 0),      (255, 128, 0),    (0, 165, 255),    (255, 0, 255),
    (0, 255, 255),    (255, 0, 0),      (147, 20, 255),   (255, 255, 0),
    (0, 128, 255),    (203, 192, 255),  (128, 255, 0),    (255, 191, 0),
]

# Zone visualization colors (BGR)
_ZONE_BORDER_COLOR = (255, 200, 50)     # Light blue
_ZONE_FILL_ALPHA = 0.12
_ENTRY_COLOR = (0, 200, 0)             # Green
_EXIT_COLOR = (0, 0, 200)              # Red

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.55
_FONT_THICKNESS = 2
_HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
_HUD_SCALE = 0.45
_HUD_COLOR = (0, 255, 255)
_HUD_THICKNESS = 1


def _get_track_color(track_id: int) -> Tuple[int, int, int]:
    return _TRACK_COLORS[(track_id - 1) % len(_TRACK_COLORS)]


class MovementVisualizer:
    """Handles visual annotation of zones, paths, tracks, and HUD for Phase 3."""

    def __init__(self, path_tracking_enabled: bool = True):
        self.path_tracking_enabled = path_tracking_enabled

    def draw_zones(self, frame: np.ndarray, zone_manager: ZoneManager) -> np.ndarray:
        """Draw zone boundaries with semi-transparent fill and labels."""
        overlay = frame.copy()

        for zone_def in zone_manager.get_all_zones():
            pts = np.array(zone_def.polygon, dtype=np.int32).reshape((-1, 1, 2))

            # Semi-transparent fill
            cv2.fillPoly(overlay, [pts], _ZONE_BORDER_COLOR)

            # Border
            cv2.polylines(frame, [pts], True, _ZONE_BORDER_COLOR, 2)

            # Zone label at centroid
            cx = int(np.mean([p[0] for p in zone_def.polygon]))
            cy = int(np.mean([p[1] for p in zone_def.polygon]))

            label = zone_def.name
            (tw, th), _ = cv2.getTextSize(label, _FONT, 0.5, 1)
            cv2.rectangle(frame, (cx - tw // 2 - 4, cy - th - 4), (cx + tw // 2 + 4, cy + 4), (0, 0, 0), -1)
            cv2.putText(frame, label, (cx - tw // 2, cy), _FONT, 0.5, _ZONE_BORDER_COLOR, 1)

        # Apply fill with transparency
        cv2.addWeighted(overlay, _ZONE_FILL_ALPHA, frame, 1 - _ZONE_FILL_ALPHA, 0, frame)
        return frame

    def draw_entry_exit_regions(self, frame: np.ndarray, zone_manager: ZoneManager) -> np.ndarray:
        """Draw entry regions (green) and exit regions (red)."""
        for region in zone_manager.get_all_entry_regions():
            pts = np.array(region.polygon, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, _ENTRY_COLOR, 2)
            cx = int(np.mean([p[0] for p in region.polygon]))
            cy = int(np.mean([p[1] for p in region.polygon]))
            cv2.putText(frame, f"ENTRY: {region.name}", (cx - 30, cy), _FONT, 0.4, _ENTRY_COLOR, 1)

        for region in zone_manager.get_all_exit_regions():
            pts = np.array(region.polygon, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, _EXIT_COLOR, 2)
            cx = int(np.mean([p[0] for p in region.polygon]))
            cy = int(np.mean([p[1] for p in region.polygon]))
            cv2.putText(frame, f"EXIT: {region.name}", (cx - 30, cy), _FONT, 0.4, _EXIT_COLOR, 1)

        return frame

    def draw_path(self, frame: np.ndarray, shopper_path: ShopperPath, track_id: int) -> np.ndarray:
        """Draw the movement trail for a tracked shopper."""
        if not self.path_tracking_enabled:
            return frame

        pts = shopper_path.get_visualization_points()
        if len(pts) < 2:
            return frame

        color = _get_track_color(track_id)
        num_pts = len(pts)

        for i in range(1, num_pts):
            thickness = max(1, int(3 * (i / num_pts)))
            cv2.line(frame, pts[i - 1], pts[i], color, thickness)
            cv2.circle(frame, pts[i], 2, color, -1)

        return frame

    def draw_track_with_zone(
        self,
        frame: np.ndarray,
        track: TrackData,
        zone_names: List[str],
    ) -> np.ndarray:
        """Draw bounding box with tracking ID, confidence, and current zone."""
        color = _get_track_color(track.track_id)
        x1, y1, x2, y2 = track.bbox

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Build label
        zone_str = ", ".join(zone_names) if zone_names else "—"
        label = f"Person {track.track_id} | {track.confidence:.2f}"
        zone_label = f"Zone: {zone_str}"

        # Draw label background
        (tw1, th1), bl1 = cv2.getTextSize(label, _FONT, _FONT_SCALE, _FONT_THICKNESS)
        (tw2, th2), bl2 = cv2.getTextSize(zone_label, _FONT, 0.45, 1)
        max_tw = max(tw1, tw2)

        bg_height = th1 + th2 + bl1 + 10
        cv2.rectangle(frame, (x1, y1 - bg_height), (x1 + max_tw + 8, y1), color, -1)

        cv2.putText(frame, label, (x1 + 2, y1 - th2 - bl2 - 6), _FONT, _FONT_SCALE, (0, 0, 0), _FONT_THICKNESS)
        cv2.putText(frame, zone_label, (x1 + 2, y1 - 4), _FONT, 0.45, (0, 0, 0), 1)

        return frame

    def draw_movement_hud(
        self,
        frame: np.ndarray,
        frame_number: int,
        active_shoppers: int,
        total_entries: int,
        total_exits: int,
        zone_occupancy: Dict[str, int],
        fps: float,
        inference_ms: float,
        tracking_ms: float,
    ) -> np.ndarray:
        """Draw extended HUD with zone occupancy and entry/exit counts."""
        lines = [
            f"Frame: {frame_number}",
            f"Active Shoppers: {active_shoppers}",
            f"Entries: {total_entries} | Exits: {total_exits}",
            f"YOLO: {inference_ms:.1f}ms | Tracker: {tracking_ms:.1f}ms",
            f"FPS: {fps:.1f}",
        ]

        # Add zone occupancy lines
        for zone_id, count in zone_occupancy.items():
            lines.append(f"  {zone_id}: {count} shoppers")

        y = 25
        for line in lines:
            cv2.putText(frame, line, (11, y + 1), _HUD_FONT, _HUD_SCALE, (0, 0, 0), _HUD_THICKNESS + 1)
            cv2.putText(frame, line, (10, y), _HUD_FONT, _HUD_SCALE, _HUD_COLOR, _HUD_THICKNESS)
            y += 18

        return frame
