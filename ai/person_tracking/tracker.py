"""
Person Tracking — ByteTrack Tracker Integration
================================================
Wraps ByteTrack to process person detections frame by frame,
maintain persistent tracking IDs, collect per-track metrics,
and manage trajectory histories.
"""

import logging
import time
from collections import deque
from typing import Dict, List, NamedTuple, Optional, Tuple

import numpy as np
# pyrefly: ignore [missing-import]
import supervision as sv
# pyrefly: ignore [missing-import]
from trackers import ByteTrackTracker

from ai.logger import setup_logger
from ai.person_detection.detector import Detection
from ai.person_tracking.config import PersonTrackingConfig
from ai.person_tracking.reid_matcher import ReIDMatcher


class TrackData(NamedTuple):
    """Active tracking data for a person in a single frame."""

    track_id: int
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    center: Tuple[int, int]  # (cx, cy)


class TrackInfo:
    """Historical tracking information for a unique person ID."""

    def __init__(
        self,
        track_id: int,
        first_frame: int,
        first_timestamp: float,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        trajectory_length: int = 30,
    ):
        self.track_id = track_id
        self.first_frame = first_frame
        self.last_frame = first_frame
        self.first_timestamp = first_timestamp
        self.last_timestamp = first_timestamp
        self.num_detections = 1
        self.total_confidence = confidence
        self.last_bbox = bbox
        
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        self.trajectory: deque = deque(maxlen=trajectory_length)
        self.trajectory.append((cx, cy))

    def update(
        self,
        frame_number: int,
        timestamp: float,
        bbox: Tuple[int, int, int, int],
        confidence: float,
    ) -> None:
        """Update track information with a new detection in the current frame."""
        self.last_frame = frame_number
        self.last_timestamp = timestamp
        self.num_detections += 1
        self.total_confidence += confidence
        self.last_bbox = bbox

        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        self.trajectory.append((cx, cy))

    @property
    def frames_tracked(self) -> int:
        """Total frame span between first and last detection."""
        return (self.last_frame - self.first_frame) + 1

    @property
    def average_confidence(self) -> float:
        """Average detection confidence across all detections of this track."""
        return self.total_confidence / self.num_detections if self.num_detections > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert track summary to dictionary for reporting."""
        return {
            "track_id": self.track_id,
            "first_frame": self.first_frame,
            "last_frame": self.last_frame,
            "frames_tracked": self.frames_tracked,
            "first_timestamp": round(self.first_timestamp, 2),
            "last_timestamp": round(self.last_timestamp, 2),
            "num_detections": self.num_detections,
            "average_confidence": round(self.average_confidence, 4),
            "last_bbox": list(self.last_bbox),
        }


class PersonTracker:
    """
    ByteTrack wrapper for multi-person tracking.
    Processes YOLO person detections and outputs active tracks with persistent IDs.
    """

    def __init__(
        self,
        config: PersonTrackingConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize ByteTrack tracker.

        Parameters
        ----------
        config : PersonTrackingConfig
            Tracking parameters and thresholds.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.config = config
        self.logger = logger or setup_logger("person_tracker")

        self.logger.info("Initializing ByteTrack tracker...")
        min_consecutive = getattr(self.config, "minimum_consecutive_frames", 3)
        self.byte_tracker = ByteTrackTracker(
            lost_track_buffer=self.config.track_buffer,
            track_activation_threshold=self.config.new_track_threshold,
            minimum_iou_threshold=self.config.match_threshold,
            high_conf_det_threshold=self.config.track_high_threshold,
            minimum_consecutive_frames=min_consecutive,
        )

        self.logger.info("ByteTrack tracker initialized successfully.")

        # Re-ID Appearance recovery matcher
        self.reid_matcher = ReIDMatcher()

        # Master track history: track_id -> TrackInfo
        self.track_history: Dict[int, TrackInfo] = {}

        # Tracking performance stats
        self.max_simultaneous_tracks: int = 0
        self.total_active_tracks_sum: int = 0
        self.processed_frames_count: int = 0

    def reset(self) -> None:
        """Reset internal tracker state and statistics."""
        self.byte_tracker.reset()
        self.reid_matcher.gallery.clear()
        self.track_history.clear()
        self.max_simultaneous_tracks = 0
        self.total_active_tracks_sum = 0
        self.processed_frames_count = 0

    def update(
        self,
        detections: List[Detection],
        frame_number: int,
        timestamp: float,
        frame: Optional[np.ndarray] = None,
    ) -> Tuple[List[TrackData], float]:
        """
        Process frame detections through ByteTrack with appearance Re-ID support.

        Parameters
        ----------
        detections : List[Detection]
            Person detections from PersonDetector.
        frame_number : int
            Current 1-indexed video frame number.
        timestamp : float
            Current video timestamp in seconds.
        frame : np.ndarray, optional
            Current raw video frame for appearance Re-ID signature extraction.

        Returns
        -------
        Tuple[List[TrackData], float]
            Active tracks in the frame and tracker processing time in milliseconds.
        """
        start = time.perf_counter()

        if not detections:
            # Empty frame handling
            sv_dets = sv.Detections.empty()
            tracked_dets = self.byte_tracker.update(sv_dets)
            tracking_time_ms = (time.perf_counter() - start) * 1000
            self.processed_frames_count += 1
            return [], tracking_time_ms

        # Convert list of Detection namedtuples into sv.Detections
        xyxy = np.array([d.bbox for d in detections], dtype=np.float32)
        confidence = np.array([d.confidence for d in detections], dtype=np.float32)
        class_id = np.array([d.class_id for d in detections], dtype=int)

        sv_dets = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
        )

        # Update ByteTrack tracker
        tracked_dets = self.byte_tracker.update(sv_dets)
        tracking_time_ms = (time.perf_counter() - start) * 1000

        active_tracks: List[TrackData] = []
        active_ids_this_frame = set()

        if tracked_dets is not None and len(tracked_dets) > 0 and tracked_dets.tracker_id is not None:
            for i in range(len(tracked_dets)):
                raw_id = int(tracked_dets.tracker_id[i])
                if raw_id < 0:
                    continue

                # 1-based persistent track ID for clear display (1, 2, 3...)
                track_id = raw_id + 1

                box = tracked_dets.xyxy[i]
                bbox = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
                conf = float(tracked_dets.confidence[i]) if tracked_dets.confidence is not None else 0.0
                cx = int((bbox[0] + bbox[2]) / 2)
                cy = int((bbox[1] + bbox[3]) / 2)

                # Re-ID recovery check on new tracks
                if frame is not None and track_id not in self.track_history:
                    recovered_id = self.reid_matcher.match_candidate(
                        frame=frame, bbox=bbox, frame_idx=frame_number
                    )
                    if recovered_id is not None and recovered_id in self.track_history:
                        track_id = recovered_id

                active_ids_this_frame.add(track_id)

                track_data = TrackData(
                    track_id=track_id,
                    bbox=bbox,
                    confidence=conf,
                    center=(cx, cy),
                )
                active_tracks.append(track_data)

                # Maintain track history
                if track_id not in self.track_history:
                    self.track_history[track_id] = TrackInfo(
                        track_id=track_id,
                        first_frame=frame_number,
                        first_timestamp=timestamp,
                        bbox=bbox,
                        confidence=conf,
                        trajectory_length=self.config.trajectory_length,
                    )
                else:
                    self.track_history[track_id].update(
                        frame_number=frame_number,
                        timestamp=timestamp,
                        bbox=bbox,
                        confidence=conf,
                    )

                # Update appearance signature in gallery
                if frame is not None:
                    self.reid_matcher.update_track(
                        track_id=track_id,
                        frame=frame,
                        bbox=bbox,
                        frame_idx=frame_number,
                    )

        # Mark disappeared tracks as lost in Re-ID matcher
        if frame is not None:
            for tid, tinfo in self.track_history.items():
                if tid not in active_ids_this_frame and tinfo.last_frame == frame_number - 1:
                    self.reid_matcher.mark_lost(tid, frame_number)


        # Update statistics
        num_active = len(active_tracks)
        self.total_active_tracks_sum += num_active
        self.processed_frames_count += 1
        if num_active > self.max_simultaneous_tracks:
            self.max_simultaneous_tracks = num_active

        return active_tracks, tracking_time_ms

    @property
    def total_unique_tracks(self) -> int:
        """Total number of unique person IDs assigned during session."""
        return len(self.track_history)

    @property
    def confirmed_unique_tracks(self) -> int:
        """
        Total number of confirmed unique person tracks, filtering out transient
        noise and single-frame detection spikes.
        """
        min_frames = getattr(self.config, "min_track_frames", 15)
        confirmed = [
            t for t in self.track_history.values()
            if t.frames_tracked >= min_frames or t.num_detections >= 5
        ]
        return len(confirmed) if confirmed else len(self.track_history)

    def get_confirmed_tracks(self, min_frames: Optional[int] = None) -> Dict[int, TrackInfo]:
        """Return dictionary of confirmed tracks meeting the minimum frame threshold."""
        threshold = min_frames if min_frames is not None else getattr(self.config, "min_track_frames", 15)
        confirmed = {
            tid: t for tid, t in self.track_history.items()
            if t.frames_tracked >= threshold or t.num_detections >= 5
        }
        return confirmed if confirmed or not self.track_history else self.track_history

    @property
    def average_active_tracks(self) -> float:
        """Average number of active tracks per frame."""
        return (
            self.total_active_tracks_sum / self.processed_frames_count
            if self.processed_frames_count > 0
            else 0.0
        )
