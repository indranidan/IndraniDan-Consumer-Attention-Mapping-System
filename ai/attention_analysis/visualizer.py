"""
Attention Analysis — Visualizer
==================================
Draws attention-related annotations on video frames including:
- Attention region polygons
- Head pose direction arrows
- Attention state labels
- HUD with real-time statistics

All annotations clearly indicate that direction is estimated
(head orientation, not eye gaze).
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.attention_analysis.attention_classifier import AttentionDirection, AttentionState
from ai.attention_analysis.attention_region_manager import AttentionRegion
from ai.attention_analysis.attention_tracker import AttentionEvent
from ai.attention_analysis.head_pose_estimator import HeadPoseResult
from ai.logger import setup_logger
from ai.movement_analysis.zone_manager import ZoneManager


# ---------------------------------------------------------------------------
# Colours and fonts
# ---------------------------------------------------------------------------
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.5
_FONT_THICKNESS = 1
_SMALL_FONT_SCALE = 0.4

# Attention region colours
_REGION_COLOR = (255, 165, 0)     # Orange for attention regions
_REGION_THICKNESS = 2
_REGION_FILL_ALPHA = 0.15

# Head pose / gaze
_FACE_BOX_COLOR = (0, 255, 255)   # Cyan for face bounding box
_ARROW_COLOR = (0, 0, 255)        # Red for attention direction arrow
_ARROW_THICKNESS = 2
_ARROW_LENGTH = 60

# Attention state colours
_ATTENDING_COLOR = (0, 255, 0)     # Green
_NOT_ATTENDING_COLOR = (128, 128, 128)  # Grey
_UNKNOWN_COLOR = (0, 165, 255)     # Orange

# HUD
_HUD_BG_COLOR = (0, 0, 0)
_HUD_TEXT_COLOR = (255, 255, 255)
_HUD_ACCENT_COLOR = (0, 255, 255)


class AttentionVisualizer:
    """
    Draws attention analysis annotations on video frames.

    Provides methods for drawing region overlays, head pose arrows,
    per-track attention labels, and a real-time HUD panel.
    """

    def __init__(
        self,
        path_tracking_enabled: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.path_tracking_enabled = path_tracking_enabled
        self.logger = logger or setup_logger("attention_visualizer")

    def draw_attention_regions(
        self,
        frame: np.ndarray,
        regions: List[AttentionRegion],
    ) -> np.ndarray:
        """Draw configured attention region polygons on the frame."""
        overlay = frame.copy()

        for region in regions:
            pts = np.array(region.polygon, dtype=np.int32)

            # Semi-transparent fill
            cv2.fillPoly(overlay, [pts], _REGION_COLOR)

            # Solid border
            cv2.polylines(frame, [pts], True, _REGION_COLOR, _REGION_THICKNESS)

            # Region label
            label = f"{region.name} [{region.type}]"
            cx, cy = region.center
            (tw, th), _ = cv2.getTextSize(label, _FONT, _SMALL_FONT_SCALE, 1)
            lx = cx - tw // 2
            ly = cy - th // 2

            cv2.rectangle(
                frame,
                (lx - 2, ly - th - 2),
                (lx + tw + 2, ly + 4),
                _REGION_COLOR,
                -1,
            )
            cv2.putText(
                frame, label, (lx, ly),
                _FONT, _SMALL_FONT_SCALE, (255, 255, 255), 1,
            )

        # Blend overlay for transparency
        cv2.addWeighted(overlay, _REGION_FILL_ALPHA, frame, 1 - _REGION_FILL_ALPHA, 0, frame)
        return frame

    def draw_zones(self, frame: np.ndarray, zone_manager: ZoneManager) -> np.ndarray:
        """Draw zone boundaries (reused from Phase 3/4)."""
        for zone in zone_manager.get_all_zones():
            pts = np.array(zone.polygon, dtype=np.int32)
            cv2.polylines(frame, [pts], True, (255, 255, 0), 1)
        return frame

    def draw_head_pose(
        self,
        frame: np.ndarray,
        pose: HeadPoseResult,
        track_id: int,
    ) -> np.ndarray:
        """
        Draw face bounding box, nose point, and attention direction arrow.

        The arrow indicates estimated head orientation direction.
        """
        if not pose.face_detected:
            return frame

        # Face bounding box
        fx1, fy1, fx2, fy2 = pose.face_bbox
        cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), _FACE_BOX_COLOR, 1)

        # Nose point
        nx, ny = pose.nose_point
        cv2.circle(frame, (nx, ny), 3, _FACE_BOX_COLOR, -1)

        # Direction arrow from nose point
        yaw_rad = math.radians(pose.yaw)
        pitch_rad = math.radians(-pose.pitch)  # Invert for image space

        dx = math.sin(yaw_rad) * _ARROW_LENGTH
        dy = math.sin(pitch_rad) * _ARROW_LENGTH

        end_x = int(nx + dx)
        end_y = int(ny + dy)

        cv2.arrowedLine(
            frame, (nx, ny), (end_x, end_y),
            _ARROW_COLOR, _ARROW_THICKNESS, tipLength=0.3,
        )

        return frame

    def draw_track_with_attention(
        self,
        frame: np.ndarray,
        track,  # TrackData from person_tracking
        zone_names: List[str],
        direction: AttentionDirection,
        target_name: Optional[str],
        confidence: float,
        state: AttentionState,
        active_dwell: Dict[str, float],
    ) -> np.ndarray:
        """
        Draw person bounding box with attention information overlay.

        Clearly labels all direction estimates as "Est." (estimated).
        """
        x1, y1, x2, y2 = track.bbox

        # Choose colour based on attention state
        if state == AttentionState.ATTENDING:
            box_color = _ATTENDING_COLOR
        elif state == AttentionState.UNKNOWN:
            box_color = _UNKNOWN_COLOR
        else:
            box_color = _NOT_ATTENDING_COLOR

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

        # Build info lines
        lines = []

        # Line 1: ID + Zone
        zone_str = ", ".join(zone_names) if zone_names else "—"
        lines.append(f"ID:{track.track_id} Zone:{zone_str}")

        # Line 2: Direction + Target
        dir_str = direction.value
        tgt_str = target_name or "—"
        lines.append(f"Est.Dir:{dir_str} Tgt:{tgt_str}")

        # Line 3: State + Confidence
        state_str = state.value
        lines.append(f"Attn:{state_str} Conf:{confidence:.2f}")

        # Line 4: Active dwell times (if any)
        if active_dwell:
            dwell_parts = [f"{z}:{dt:.1f}s" for z, dt in active_dwell.items()]
            lines.append(f"Dwell: {', '.join(dwell_parts)}")

        # Draw text above bounding box
        y_offset = y1 - 5
        for line in reversed(lines):
            (tw, th), baseline = cv2.getTextSize(
                line, _FONT, _SMALL_FONT_SCALE, 1
            )
            bg_y1 = y_offset - th - 4
            bg_y2 = y_offset + 2

            cv2.rectangle(
                frame,
                (x1, bg_y1),
                (x1 + tw + 4, bg_y2),
                _HUD_BG_COLOR,
                -1,
            )
            cv2.putText(
                frame, line, (x1 + 2, y_offset - 2),
                _FONT, _SMALL_FONT_SCALE, box_color, 1,
            )
            y_offset = bg_y1 - 2

        return frame

    def draw_path(self, frame: np.ndarray, path, track_id: int) -> np.ndarray:
        """Draw trajectory path (reused from Phase 3/4)."""
        if path is None:
            return frame

        if hasattr(path, "get_visualization_points"):
            pts = path.get_visualization_points()
        else:
            pts = path

        if not pts or len(pts) < 2:
            return frame

        color = self._track_color(track_id)
        for i in range(1, len(pts)):
            p1 = pts[i - 1]
            p2 = pts[i]
            # Handle both tuple and object path point formats
            if isinstance(p1, tuple):
                pt1 = (int(p1[0]), int(p1[1]))
                pt2 = (int(p2[0]), int(p2[1]))
            else:
                pt1 = (int(p1.x), int(p1.y))
                pt2 = (int(p2.x), int(p2.y))
            cv2.line(frame, pt1, pt2, color, 1)

        return frame

    def draw_attention_hud(
        self,
        frame: np.ndarray,
        frame_number: int,
        active_shoppers: int,
        valid_head_poses: int,
        attention_targets: int,
        unknown_estimates: int,
        fps: float,
        inference_ms: float,
        tracking_ms: float,
    ) -> np.ndarray:
        """
        Draw a HUD panel with attention analysis statistics.

        All attention values are labeled as estimated.
        """
        lines = [
            f"Frame: {frame_number}",
            f"Active Shoppers: {active_shoppers}",
            f"Valid Head Poses: {valid_head_poses}",
            f"Est. Attention Targets: {attention_targets}",
            f"Unknown Estimates: {unknown_estimates}",
            f"FPS: {fps:.1f}",
            f"Inference: {inference_ms:.1f}ms",
            f"Tracking: {tracking_ms:.1f}ms",
        ]

        # HUD background
        hud_h = len(lines) * 22 + 16
        hud_w = 280
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 5), (5 + hud_w, 5 + hud_h), _HUD_BG_COLOR, -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # HUD text
        for i, line in enumerate(lines):
            y = 24 + i * 22
            color = _HUD_ACCENT_COLOR if i == 0 else _HUD_TEXT_COLOR
            cv2.putText(
                frame, line, (12, y),
                _FONT, _SMALL_FONT_SCALE, color, 1,
            )

        return frame

    def draw_entry_exit_regions(
        self, frame: np.ndarray, zone_manager: ZoneManager
    ) -> np.ndarray:
        """Draw entry/exit regions (reused from Phase 3/4)."""
        for region in zone_manager.get_all_entry_regions():
            pts = np.array(region.polygon, dtype=np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 1)

        for region in zone_manager.get_all_exit_regions():
            pts = np.array(region.polygon, dtype=np.int32)
            cv2.polylines(frame, [pts], True, (0, 0, 255), 1)

        return frame

    @staticmethod
    def _track_color(track_id: int) -> Tuple[int, int, int]:
        """Generate a deterministic colour for a track ID."""
        hue = (track_id * 47) % 180
        color_hsv = np.array([[[hue, 200, 220]]], dtype=np.uint8)
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        return (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))
