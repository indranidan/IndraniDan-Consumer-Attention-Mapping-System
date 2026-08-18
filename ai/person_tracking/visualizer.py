"""
Person Tracking — Track Visualizer
===================================
Annotates video frames with person bounding boxes, persistent tracking IDs,
detection confidence scores, motion trajectories, and HUD metrics.
"""

import math
from typing import Dict, List, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.person_tracking.config import PersonTrackingConfig
from ai.person_tracking.tracker import TrackData, TrackInfo

# Distinct color palette for persistent tracking IDs (BGR format)
_TRACK_COLORS = [
    (0, 255, 0),      # Bright Green
    (255, 128, 0),    # Cyan Blue
    (0, 165, 255),    # Orange
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Yellow
    (255, 0, 0),      # Blue
    (147, 20, 255),   # Pink/Deep Pink
    (255, 255, 0),    # Cyan
    (0, 128, 255),    # Amber
    (203, 192, 255),  # Light Pink
    (128, 255, 0),    # Lime
    (255, 191, 0),    # Deep Sky Blue
]

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.55
_FONT_THICKNESS = 2
_BOX_THICKNESS = 2

_HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
_HUD_SCALE = 0.50
_HUD_COLOR = (0, 255, 255)  # Cyan
_HUD_THICKNESS = 1


def _get_track_color(track_id: int) -> Tuple[int, int, int]:
    """Return a consistent color for a given tracking ID."""
    return _TRACK_COLORS[(track_id - 1) % len(_TRACK_COLORS)]


class TrackVisualizer:
    """Handles visual annotation of tracks, trajectories, and HUD."""

    def __init__(self, config: PersonTrackingConfig):
        """
        Initialize track visualizer.

        Parameters
        ----------
        config : PersonTrackingConfig
            Configuration controlling trajectory enabling, etc.
        """
        self.config = config

    def annotate(
        self,
        frame: np.ndarray,
        active_tracks: List[TrackData],
        track_history: Dict[int, TrackInfo],
    ) -> np.ndarray:
        """
        Draw bounding boxes, tracking labels, and optional trajectories.

        Parameters
        ----------
        frame : np.ndarray
            Original BGR OpenCV frame.
        active_tracks : List[TrackData]
            List of active tracks in the frame.
        track_history : Dict[int, TrackInfo]
            Master history dictionary mapping track_id to TrackInfo.

        Returns
        -------
        np.ndarray
            Annotated frame copy.
        """
        annotated = frame.copy()

        # 1. Draw trajectories first (behind bounding boxes)
        if self.config.trajectory_enabled:
            for track in active_tracks:
                track_info = track_history.get(track.track_id)
                if track_info and len(track_info.trajectory) > 1:
                    color = _get_track_color(track.track_id)
                    pts = list(track_info.trajectory)
                    
                    # Draw connected path lines with fading thickness/opacity
                    num_pts = len(pts)
                    for i in range(1, num_pts):
                        pt1 = pts[i - 1]
                        pt2 = pts[i]
                        thickness = max(1, int(3 * (i / num_pts)))
                        cv2.line(annotated, pt1, pt2, color, thickness)
                        cv2.circle(annotated, pt2, 2, color, -1)

        # 2. Draw bounding boxes and labels for active tracks
        for track in active_tracks:
            color = _get_track_color(track.track_id)
            x1, y1, x2, y2 = track.bbox

            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, _BOX_THICKNESS)

            # Label text: "Person 7 | 0.91"
            label = f"Person {track.track_id} | {track.confidence:.2f}"
            (text_w, text_h), baseline = cv2.getTextSize(
                label, _FONT, _FONT_SCALE, _FONT_THICKNESS
            )

            # Text background rectangle
            cv2.rectangle(
                annotated,
                (x1, y1 - text_h - baseline - 4),
                (x1 + text_w + 4, y1),
                color,
                -1,
            )

            # Draw text in contrasting color (black or white depending on background brightness)
            text_color = (0, 0, 0)
            cv2.putText(
                annotated,
                label,
                (x1 + 2, y1 - baseline - 2),
                _FONT,
                _FONT_SCALE,
                text_color,
                _FONT_THICKNESS,
            )

        return annotated

    def draw_hud(
        self,
        frame: np.ndarray,
        frame_number: int,
        active_tracks_count: int,
        detections_count: int,
        inference_time_ms: float,
        tracking_time_ms: float,
        fps: float,
    ) -> np.ndarray:
        """
        Draw a heads-up display overlay on the annotated frame.

        Parameters
        ----------
        frame : np.ndarray
            Frame image.
        frame_number : int
            Current frame number.
        active_tracks_count : int
            Number of active tracks in current frame.
        detections_count : int
            Number of raw YOLO detections in current frame.
        inference_time_ms : float
            YOLO inference time in ms.
        tracking_time_ms : float
            ByteTrack processing time in ms.
        fps : float
            Overall processing FPS.

        Returns
        -------
        np.ndarray
            Frame with HUD overlay.
        """
        lines = [
            f"Frame: {frame_number}",
            f"Active Tracks: {active_tracks_count}",
            f"Detections: {detections_count}",
            f"YOLO Time: {inference_time_ms:.1f}ms",
            f"ByteTrack Time: {tracking_time_ms:.1f}ms",
            f"Processing FPS: {fps:.1f}",
        ]

        y = 25
        for line in lines:
            # Draw subtle text background shadow
            cv2.putText(
                frame,
                line,
                (11, y + 1),
                _HUD_FONT,
                _HUD_SCALE,
                (0, 0, 0),
                _HUD_THICKNESS + 1,
            )
            cv2.putText(
                frame,
                line,
                (10, y),
                _HUD_FONT,
                _HUD_SCALE,
                _HUD_COLOR,
                _HUD_THICKNESS,
            )
            y += 20

        return frame
