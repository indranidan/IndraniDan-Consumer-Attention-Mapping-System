"""
Dwell-Time Analysis — Video Processor
=======================================
Orchestrates the full Phase 4 pipeline: OpenCV capture → YOLOv8 detection →
ByteTrack tracking → path tracking → zone detection → entry/exit monitoring →
dwell-time tracking → session management → annotated output video.
Reuses Phase 1-3 infrastructure.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# pyrefly: ignore [missing-import]
import cv2

from ai.logger import setup_logger
from ai.dwell_time_analysis.config import DwellTimeConfig
from ai.dwell_time_analysis.dwell_tracker import DwellTracker
from ai.dwell_time_analysis.visualizer import DwellVisualizer
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.person_detection.detector import PersonDetector
from ai.person_tracking.tracker import PersonTracker
from ai.utils import ensure_directory


class DwellVideoProcessor:
    """
    Manages the full Phase 4 dwell-time video processing pipeline.
    Processes video frames sequentially, updates dwell state frame-by-frame,
    and produces annotated output video and metrics.
    """

    _LOG_INTERVAL = 50

    def __init__(
        self,
        source: str,
        config: DwellTimeConfig,
        detector: PersonDetector,
        tracker: PersonTracker,
        zone_manager: ZoneManager,
        path_tracker: PathTracker,
        zone_tracker: ZoneTracker,
        entry_exit_monitor: EntryExitMonitor,
        session_manager: SessionManager,
        dwell_tracker: DwellTracker,
        visualizer: DwellVisualizer,
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
        self.dwell_tracker = dwell_tracker
        self.visualizer = visualizer
        self.logger = logger or setup_logger("dwell_video_processor")

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

    def close(self) -> None:
        """Release video capture resources."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Video capture released.")

    def process_video_file(self) -> Dict:
        """
        Process video file through the full Phase 4 pipeline.

        Returns
        -------
        Dict
            Processing statistics and metadata for report generation.
        """
        self.open()
        self.tracker.reset()

        ensure_directory(self.config.videos_dir)
        ensure_directory(self.config.reports_dir)
        ensure_directory(self.config.plots_dir)

        source_name = Path(self.source).stem
        output_video_path = self.config.videos_dir / f"{source_name}_dwell_analysis.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_video_path), fourcc, self.fps, (self.width, self.height))
        if not writer.isOpened():
            self.close()
            raise RuntimeError(f"Failed to create VideoWriter at: {output_video_path}")

        self.logger.info(f"Output video: {output_video_path}")
        self.logger.info("Starting dwell-time analysis pipeline...")

        zone_names_map = {z.id: z.name for z in self.zone_manager.get_all_zones()}

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

                # Layer 1: Zone boundaries and entry/exit regions
                if self.config.movement_config.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)
                if self.config.movement_config.entry_exit_enabled:
                    annotated = self.visualizer.draw_entry_exit_regions(annotated, self.zone_manager)

                # Step 3-6: Per-track processing
                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    current_active_ids.add(tid)

                    # Path tracking
                    if self.config.movement_config.path_tracking_enabled:
                        self.path_tracker.update(tid, frame_number, timestamp, cx, cy)

                    # Spatial Zone detection (Phase 3)
                    current_zone_ids = []
                    if self.config.movement_config.zone_tracking_enabled:
                        current_zone_ids = self.zone_tracker.update(tid, frame_number, timestamp, cx, cy)

                    # Entry/exit monitoring (Phase 3)
                    if self.config.movement_config.entry_exit_enabled:
                        self.entry_exit_monitor.update(tid, frame_number, timestamp, cx, cy)

                    # Dwell-time tracking (Phase 4)
                    if self.config.dwell_time_enabled and self.config.movement_config.zone_tracking_enabled:
                        self.dwell_tracker.update(
                            track_id=tid,
                            frame=frame_number,
                            timestamp=timestamp,
                            current_zone_ids=current_zone_ids,
                            zone_names=zone_names_map,
                            confidence=track.confidence,
                        )

                    # Session update (Phase 3)
                    self.session_manager.update_session(tid, frame_number, timestamp, track.confidence)

                    # Visualization: path trail
                    if self.config.movement_config.path_tracking_enabled:
                        path = self.path_tracker.get_path(tid)
                        if path:
                            annotated = self.visualizer.draw_path(annotated, path, tid)

                    # Visualization: bounding box with live dwell time
                    zone_names = self.zone_tracker.get_current_zone_names(tid) if self.config.movement_config.zone_tracking_enabled else []
                    active_dt = self.dwell_tracker.get_active_dwell_times(tid, timestamp) if self.config.dwell_time_enabled else {}
                    annotated = self.visualizer.draw_track_with_dwell(annotated, track, zone_names, active_dt)

                # Detect lost tracks (disappeared in this frame)
                lost_ids = previous_active_ids - current_active_ids
                for lost_id in lost_ids:
                    lost_timestamp = (frame_number - 1) / self.fps if self.fps > 0 else 0.0
                    if self.config.movement_config.entry_exit_enabled:
                        self.entry_exit_monitor.mark_track_lost(lost_id, frame_number - 1, lost_timestamp)
                    if self.config.movement_config.zone_tracking_enabled:
                        self.zone_tracker.close_track(lost_id, frame_number - 1, lost_timestamp)
                    if self.config.dwell_time_enabled:
                        self.dwell_tracker.handle_lost_track(lost_id, frame_number - 1, lost_timestamp)

                previous_active_ids = current_active_ids

                # Draw extended Dwell HUD
                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                active_dwell_info = {}
                if self.config.dwell_time_enabled:
                    active_visits = self.dwell_tracker.get_active_visits()
                    for v in active_visits:
                        dt = timestamp - v.entry_time
                        active_dwell_info[v.zone_name] = max(active_dwell_info.get(v.zone_name, 0.0), dt)

                annotated = self.visualizer.draw_dwell_hud(
                    frame=annotated,
                    frame_number=frame_number,
                    active_shoppers=len(active_tracks),
                    active_zone_visits=self.dwell_tracker.total_active_visits,
                    active_dwell_info=active_dwell_info,
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

                    dwell_log = ""
                    if active_dwell_info:
                        parts = [f"{z}: {dt:.1f} sec" for z, dt in active_dwell_info.items()]
                        dwell_log = f" | Active Dwell: {', '.join(parts)}"

                    self.logger.info(
                        f"Frame: {frame_number}{progress} | "
                        f"Active shoppers: {len(active_tracks)} | "
                        f"Active zone visits: {self.dwell_tracker.total_active_visits}"
                        f"{dwell_log}"
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
        final_timestamp = frame_number / self.fps if self.fps > 0 else 0.0

        # Close remaining active dwell visits at video end
        self.dwell_tracker.close_remaining_visits(frame_number, final_timestamp, status="completed")

        self.logger.info("Processing completed.")
        self.logger.info(f"Unique shoppers: {self.tracker.total_unique_tracks}")
        self.logger.info(f"Completed zone visits: {self.dwell_tracker.total_completed_events}")
        self.logger.info(f"Track-lost visits: {self.dwell_tracker.total_track_lost_events}")

        # Finalize Phase 3 sessions
        self.session_manager.finalize_all(
            path_tracker=self.path_tracker,
            zone_tracker=self.zone_tracker,
            entry_exit_monitor=self.entry_exit_monitor,
        )

        processing_stats = {
            "video_filename": Path(self.source).name,
            "video_path": str(Path(self.source).resolve()),
            "video_duration_sec": round(self.duration_sec, 2),
            "video_resolution": f"{self.width}x{self.height}",
            "video_fps": round(self.fps, 2),
            "total_frames_processed": frame_number,
            "total_unique_shoppers": self.tracker.total_unique_tracks,
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
            "track_buffer": self.config.movement_config.tracking_config.track_buffer,
            "gap_tolerance": self.config.dwell_track_gap_tolerance,
            "output_video": str(output_video_path),
        }

        return processing_stats

    def process_webcam(self) -> None:
        """Process live webcam feed with dwell-time HUD overlays. Press 'q' to quit."""
        self.open()
        self.tracker.reset()

        self.logger.info("Starting live dwell-time analysis from webcam...")
        self.logger.info("Press 'q' to quit.")

        zone_names_map = {z.id: z.name for z in self.zone_manager.get_all_zones()}

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

                if self.config.movement_config.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)
                if self.config.movement_config.entry_exit_enabled:
                    annotated = self.visualizer.draw_entry_exit_regions(annotated, self.zone_manager)

                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    current_active_ids.add(tid)

                    if self.config.movement_config.path_tracking_enabled:
                        self.path_tracker.update(tid, frame_number, timestamp, cx, cy)

                    current_zone_ids = []
                    if self.config.movement_config.zone_tracking_enabled:
                        current_zone_ids = self.zone_tracker.update(tid, frame_number, timestamp, cx, cy)

                    if self.config.movement_config.entry_exit_enabled:
                        self.entry_exit_monitor.update(tid, frame_number, timestamp, cx, cy)

                    if self.config.dwell_time_enabled and self.config.movement_config.zone_tracking_enabled:
                        self.dwell_tracker.update(
                            track_id=tid, frame=frame_number, timestamp=timestamp,
                            current_zone_ids=current_zone_ids, zone_names=zone_names_map,
                            confidence=track.confidence,
                        )

                    zone_names = self.zone_tracker.get_current_zone_names(tid) if self.config.movement_config.zone_tracking_enabled else []
                    active_dt = self.dwell_tracker.get_active_dwell_times(tid, timestamp) if self.config.dwell_time_enabled else {}
                    annotated = self.visualizer.draw_track_with_dwell(annotated, track, zone_names, active_dt)

                lost_ids = previous_active_ids - current_active_ids
                for lost_id in lost_ids:
                    lost_timestamp = (frame_number - 1) / self.fps if self.fps > 0 else 0.0
                    if self.config.movement_config.entry_exit_enabled:
                        self.entry_exit_monitor.mark_track_lost(lost_id, frame_number - 1, lost_timestamp)
                    if self.config.movement_config.zone_tracking_enabled:
                        self.zone_tracker.close_track(lost_id, frame_number - 1, lost_timestamp)
                    if self.config.dwell_time_enabled:
                        self.dwell_tracker.handle_lost_track(lost_id, frame_number - 1, lost_timestamp)

                previous_active_ids = current_active_ids

                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                active_dwell_info = {}
                if self.config.dwell_time_enabled:
                    for v in self.dwell_tracker.get_active_visits():
                        dt = timestamp - v.entry_time
                        active_dwell_info[v.zone_name] = max(active_dwell_info.get(v.zone_name, 0.0), dt)

                annotated = self.visualizer.draw_dwell_hud(
                    frame=annotated, frame_number=frame_number,
                    active_shoppers=len(active_tracks),
                    active_zone_visits=self.dwell_tracker.total_active_visits,
                    active_dwell_info=active_dwell_info, fps=current_fps,
                    inference_ms=inference_ms, tracking_ms=tracking_ms,
                )

                cv2.imshow("Dwell-Time Analysis — Press 'q' to quit", annotated)
                if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
                    self.logger.info("Quit signal received.")
                    break

        except KeyboardInterrupt:
            self.logger.info("Webcam session interrupted.")
        finally:
            cv2.destroyAllWindows()
            self.close()

        self.logger.info(f"Webcam session ended. Frames: {frame_number}")
