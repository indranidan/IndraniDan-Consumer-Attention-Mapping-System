"""
Movement Analysis — Video Processor
======================================
Orchestrates the full Phase 3 pipeline: OpenCV capture → YOLOv8 detection →
ByteTrack tracking → path tracking → zone detection → entry/exit monitoring →
session management → annotated output video.
Reuses PersonDetector and PersonTracker from Phase 1/2.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# pyrefly: ignore [missing-import]
import cv2

from ai.logger import setup_logger
from ai.movement_analysis.config import MovementAnalysisConfig
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.movement_visualizer import MovementVisualizer
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.traffic_analyzer import TrafficAnalyzer
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.person_detection.detector import PersonDetector
from ai.person_tracking.tracker import PersonTracker
from ai.utils import ensure_directory


class MovementVideoProcessor:
    """
    Manages the full Phase 3 movement analysis pipeline.
    Reads video frames, runs detection+tracking, updates all analytics
    modules per frame, and generates annotated output video.
    """

    _LOG_INTERVAL = 50

    def __init__(
        self,
        source: str,
        config: MovementAnalysisConfig,
        detector: PersonDetector,
        tracker: PersonTracker,
        zone_manager: ZoneManager,
        path_tracker: PathTracker,
        zone_tracker: ZoneTracker,
        entry_exit_monitor: EntryExitMonitor,
        session_manager: SessionManager,
        visualizer: MovementVisualizer,
        logger: Optional[logging.Logger] = None,
    ):
        self.source = source
        self.config = config
        self.detector = detector
        self.tracker = tracker
        self.zone_manager = zone_manager
        self.path_tracker = path_tracker
        self.zone_tracker = zone_tracker
        self.entry_exit_monitor = entry_exit_monitor
        self.session_manager = session_manager
        self.visualizer = visualizer
        self.logger = logger or setup_logger("movement_video_processor")

        # Source type detection
        self.is_webcam = False
        self.webcam_index = -1
        try:
            self.webcam_index = int(source)
            self.is_webcam = True
        except (ValueError, TypeError):
            pass

        # OpenCV capture state
        self.cap: Optional[cv2.VideoCapture] = None
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 0.0
        self.total_frames: int = 0
        self.duration_sec: float = 0.0

    def open(self) -> None:
        """Open video source."""
        if self.is_webcam:
            self.logger.info(f"Opening webcam (index {self.webcam_index})...")
            self.cap = cv2.VideoCapture(self.webcam_index)
            if not self.cap.isOpened():
                raise RuntimeError(f"Cannot open webcam at index {self.webcam_index}.")
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = 0
            self.logger.info(f"Webcam opened: {self.width}x{self.height} @ {self.fps:.1f} FPS")
        else:
            video_path = Path(self.source)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            if not video_path.is_file():
                raise ValueError(f"Not a file: {video_path}")

            self.logger.info(f"Opening video file: {video_path}")
            self.cap = cv2.VideoCapture(str(video_path))
            if not self.cap.isOpened():
                raise RuntimeError(f"Cannot open video file: {video_path}")

            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0.0

            self.logger.info(
                f"Video opened: {self.width}x{self.height} @ {self.fps:.1f} FPS | "
                f"Frames: {self.total_frames:,} | Duration: {self.duration_sec:.1f}s"
            )
        if self.width > 0 and self.height > 0:
            self.zone_manager.scale_to_frame_size(self.width, self.height)

    def close(self) -> None:
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Video capture released.")

    def process_video_file(self) -> Dict:
        """
        Process video file through the full Phase 3 pipeline.

        Returns
        -------
        Dict
            Session statistics and processing metadata.
        """
        self.open()
        self.tracker.reset()

        ensure_directory(self.config.videos_dir)
        ensure_directory(self.config.reports_dir)

        source_name = Path(self.source).stem
        output_video_path = self.config.videos_dir / f"{source_name}_movement_analysis.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_video_path), fourcc, self.fps, (self.width, self.height))
        if not writer.isOpened():
            self.close()
            raise RuntimeError(f"Failed to create VideoWriter at: {output_video_path}")

        self.logger.info(f"Output video: {output_video_path}")
        self.logger.info("Starting movement analysis pipeline...")

        # Traffic analyzer for per-frame counts
        traffic_analyzer = TrafficAnalyzer(
            zone_manager=self.zone_manager,
            zone_tracker=self.zone_tracker,
            entry_exit_monitor=self.entry_exit_monitor,
            session_manager=self.session_manager,
            video_fps=self.fps,
            logger=self.logger,
        )

        frame_number = 0
        total_inference_ms = 0.0
        total_tracking_ms = 0.0
        pipeline_start = time.perf_counter()
        previous_active_ids: Set[int] = set()

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                frame_number += 1
                timestamp = frame_number / self.fps if self.fps > 0 else 0.0

                # Step 1: YOLOv8 Person Detection (Phase 1)
                detections, inference_ms = self.detector.detect(frame)
                total_inference_ms += inference_ms

                # Step 2: ByteTrack Tracking (Phase 2)
                active_tracks, tracking_ms = self.tracker.update(
                    detections=detections, frame_number=frame_number, timestamp=timestamp
                )
                total_tracking_ms += tracking_ms

                current_active_ids: Set[int] = set()
                annotated = frame.copy()

                # Draw zones and entry/exit regions first (background layer)
                if self.config.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)
                if self.config.entry_exit_enabled:
                    annotated = self.visualizer.draw_entry_exit_regions(annotated, self.zone_manager)

                # Step 3–6: Per-track analytics
                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    foot_x = cx
                    foot_y = int(track.bbox[3])
                    current_active_ids.add(tid)

                    # Path tracking
                    if self.config.path_tracking_enabled:
                        self.path_tracker.update(tid, frame_number, timestamp, cx, cy)

                    # Zone tracking (ground contact point)
                    current_zones = []
                    if self.config.zone_tracking_enabled:
                        current_zones = self.zone_tracker.update(tid, frame_number, timestamp, foot_x, foot_y)

                    # Entry/exit monitoring (ground contact point)
                    if self.config.entry_exit_enabled:
                        self.entry_exit_monitor.update(tid, frame_number, timestamp, foot_x, foot_y)

                    # Session update (with spatial-temporal position for trajectory stitching)
                    self.session_manager.update_session(
                        track_id=tid,
                        frame=frame_number,
                        timestamp=timestamp,
                        confidence=track.confidence,
                        position=(foot_x, foot_y),
                        bbox=track.bbox,
                    )

                    # Visualization: path
                    if self.config.path_tracking_enabled:
                        path = self.path_tracker.get_path(tid)
                        if path:
                            annotated = self.visualizer.draw_path(annotated, path, tid)

                    # Visualization: track with zone label
                    zone_names = []
                    if self.config.zone_tracking_enabled:
                        zone_names = self.zone_tracker.get_current_zone_names(tid)
                    annotated = self.visualizer.draw_track_with_zone(annotated, track, zone_names)

                # Detect lost tracks
                lost_ids = previous_active_ids - current_active_ids
                for lost_id in lost_ids:
                    lost_timestamp = (frame_number - 1) / self.fps if self.fps > 0 else 0.0
                    if self.config.entry_exit_enabled:
                        self.entry_exit_monitor.mark_track_lost(lost_id, frame_number - 1, lost_timestamp)
                    if self.config.zone_tracking_enabled:
                        self.zone_tracker.close_track(lost_id, frame_number - 1, lost_timestamp)

                previous_active_ids = current_active_ids

                # Record active count for traffic stats
                traffic_analyzer.record_frame_active_count(len(active_tracks))

                # Draw HUD
                zone_occupancy = {}
                if self.config.zone_tracking_enabled:
                    zone_occupancy = self.zone_tracker.get_current_zone_occupancy()

                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                annotated = self.visualizer.draw_movement_hud(
                    frame=annotated,
                    frame_number=frame_number,
                    active_shoppers=len(active_tracks),
                    total_entries=self.entry_exit_monitor.total_entries,
                    total_exits=self.entry_exit_monitor.total_exits,
                    zone_occupancy=zone_occupancy,
                    fps=current_fps,
                    inference_ms=inference_ms,
                    tracking_ms=tracking_ms,
                )

                writer.write(annotated)

                # Periodic logging
                if frame_number % self._LOG_INTERVAL == 0 or frame_number == 1:
                    progress = ""
                    if self.total_frames > 0:
                        pct = (frame_number / self.total_frames) * 100
                        progress = f" ({pct:.1f}%)"

                    zone_info = ""
                    if self.config.zone_tracking_enabled:
                        zone_parts = [f"{zid}: {cnt}" for zid, cnt in zone_occupancy.items()]
                        zone_info = f" | Zones: {', '.join(zone_parts)}" if zone_parts else ""

                    self.logger.info(
                        f"Frame {frame_number}{progress} | "
                        f"Active: {len(active_tracks)} | "
                        f"Entries: {self.entry_exit_monitor.total_entries} | "
                        f"Exits: {self.entry_exit_monitor.total_exits}"
                        f"{zone_info} | FPS: {current_fps:.1f}"
                    )

        except KeyboardInterrupt:
            self.logger.warning("Pipeline interrupted by user (Ctrl+C).")
        except MemoryError:
            self.logger.error("Out of memory during frame processing.")
            raise
        finally:
            writer.release()
            self.close()

        pipeline_elapsed = time.perf_counter() - pipeline_start

        self.logger.info("Movement analysis processing completed.")
        self.logger.info(f"Unique shoppers: {self.tracker.total_unique_tracks}")
        self.logger.info(f"Entries: {self.entry_exit_monitor.total_entries}")
        self.logger.info(f"Exits: {self.entry_exit_monitor.total_exits}")

        # Finalize sessions
        self.logger.info("Generating sessions...")
        self.session_manager.finalize_all(
            path_tracker=self.path_tracker,
            zone_tracker=self.zone_tracker,
            entry_exit_monitor=self.entry_exit_monitor,
        )

        # Generate traffic stats
        traffic_stats = traffic_analyzer.generate_stats()

        # Finalize sessions with minimum lifetime noise filtering
        min_cutoff = getattr(self.config.tracking_config, "min_track_frames", 15)
        self.session_manager.finalize_all(
            self.path_tracker,
            self.zone_tracker,
            self.entry_exit_monitor,
            min_frames=min_cutoff,
        )

        session_stats = {
            "video_filename": Path(self.source).name,
            "video_path": str(Path(self.source).resolve()),
            "video_duration_sec": round(self.duration_sec, 2),
            "video_resolution": f"{self.width}x{self.height}",
            "video_fps": round(self.fps, 2),
            "total_frames_processed": frame_number,
            "total_unique_shoppers": self.session_manager.get_confirmed_count() or self.tracker.confirmed_unique_tracks,
            "total_entries": self.entry_exit_monitor.total_entries,
            "total_exits": self.entry_exit_monitor.total_exits,
            "total_track_lost": self.entry_exit_monitor.total_track_lost,
            "max_simultaneous_shoppers": self.tracker.max_simultaneous_tracks,
            "average_active_shoppers": round(self.tracker.average_active_tracks, 2),
            "average_yolo_inference_ms": round(total_inference_ms / frame_number if frame_number > 0 else 0.0, 2),
            "average_tracking_ms": round(total_tracking_ms / frame_number if frame_number > 0 else 0.0, 2),
            "total_pipeline_time_sec": round(pipeline_elapsed, 2),
            "processing_fps": round(frame_number / pipeline_elapsed if pipeline_elapsed > 0 else 0.0, 2),
            "device": self.detector.device,
            "model": str(self.detector.model_path),
            "tracker": "ByteTrack",
            "output_video": str(output_video_path),
            "traffic_stats": traffic_stats,
        }

        return session_stats

    def process_webcam(self) -> None:
        """Process live webcam feed with movement analysis overlays. Press 'q' to quit."""
        self.open()
        self.tracker.reset()

        self.logger.info("Starting live movement analysis from webcam...")
        self.logger.info("Press 'q' to quit.")

        frame_number = 0
        pipeline_start = time.perf_counter()
        previous_active_ids: Set[int] = set()

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.warning("Failed to read webcam frame.")
                    break

                frame_number += 1
                timestamp = frame_number / self.fps if self.fps > 0 else 0.0

                detections, inference_ms = self.detector.detect(frame)
                active_tracks, tracking_ms = self.tracker.update(
                    detections=detections, frame_number=frame_number, timestamp=timestamp
                )

                current_active_ids: Set[int] = set()
                annotated = frame.copy()

                if self.config.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)
                if self.config.entry_exit_enabled:
                    annotated = self.visualizer.draw_entry_exit_regions(annotated, self.zone_manager)

                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    current_active_ids.add(tid)

                    if self.config.path_tracking_enabled:
                        self.path_tracker.update(tid, frame_number, timestamp, cx, cy)
                    current_zones = []
                    if self.config.zone_tracking_enabled:
                        current_zones = self.zone_tracker.update(tid, frame_number, timestamp, cx, cy)
                    if self.config.entry_exit_enabled:
                        self.entry_exit_monitor.update(tid, frame_number, timestamp, cx, cy)

                    if self.config.path_tracking_enabled:
                        path = self.path_tracker.get_path(tid)
                        if path:
                            annotated = self.visualizer.draw_path(annotated, path, tid)

                    zone_names = self.zone_tracker.get_current_zone_names(tid) if self.config.zone_tracking_enabled else []
                    annotated = self.visualizer.draw_track_with_zone(annotated, track, zone_names)

                lost_ids = previous_active_ids - current_active_ids
                for lost_id in lost_ids:
                    if self.config.entry_exit_enabled:
                        self.entry_exit_monitor.mark_track_lost(lost_id, frame_number - 1, timestamp)
                    if self.config.zone_tracking_enabled:
                        self.zone_tracker.close_track(lost_id, frame_number - 1, timestamp)

                previous_active_ids = current_active_ids

                zone_occupancy = self.zone_tracker.get_current_zone_occupancy() if self.config.zone_tracking_enabled else {}
                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                annotated = self.visualizer.draw_movement_hud(
                    frame=annotated, frame_number=frame_number,
                    active_shoppers=len(active_tracks),
                    total_entries=self.entry_exit_monitor.total_entries,
                    total_exits=self.entry_exit_monitor.total_exits,
                    zone_occupancy=zone_occupancy, fps=current_fps,
                    inference_ms=inference_ms, tracking_ms=tracking_ms,
                )

                cv2.imshow("Movement Analysis — Press 'q' to quit", annotated)
                if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
                    self.logger.info("Quit signal received.")
                    break

        except KeyboardInterrupt:
            self.logger.info("Webcam session interrupted.")
        finally:
            cv2.destroyAllWindows()
            self.close()

        self.logger.info(f"Webcam session ended. Frames: {frame_number}")
