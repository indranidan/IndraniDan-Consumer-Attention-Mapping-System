"""
Attention Analysis — Video Processor
========================================
Orchestrates the full Phase 5 attention analysis pipeline:
OpenCV capture → YOLOv8 detection → ByteTrack tracking → path/zone/dwell →
head pose estimation → attention classification → temporal smoothing →
attention target association → attention events → annotated output video.

Reuses Phase 1-4 infrastructure. Does NOT duplicate person detection,
tracking, zone management, or dwell-time logic.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

# pyrefly: ignore [missing-import]
import cv2

from ai.attention_analysis.attention_classifier import (
    AttentionClassifier,
    AttentionDirection,
    AttentionState,
)
from ai.attention_analysis.attention_region_manager import AttentionRegionManager
from ai.attention_analysis.attention_tracker import AttentionTracker
from ai.attention_analysis.config import AttentionAnalysisConfig
from ai.attention_analysis.head_pose_estimator import HeadPoseEstimator, HeadPoseResult, NO_DETECTION
from ai.attention_analysis.temporal_smoother import TemporalSmoother
from ai.attention_analysis.visualizer import AttentionVisualizer
from ai.dwell_time_analysis.dwell_tracker import DwellTracker
from ai.logger import setup_logger
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.person_detection.detector import PersonDetector
from ai.person_tracking.tracker import PersonTracker
from ai.utils import ensure_directory


class AttentionVideoProcessor:
    """
    Full Phase 5 attention analysis video processing pipeline.

    Processes video frames sequentially, reuses Phase 1-4 components,
    and adds head pose estimation with attention target association.
    """

    _LOG_INTERVAL = 50

    def __init__(
        self,
        source: str,
        config: AttentionAnalysisConfig,
        detector: PersonDetector,
        tracker: PersonTracker,
        zone_manager: ZoneManager,
        path_tracker: PathTracker,
        zone_tracker: ZoneTracker,
        entry_exit_monitor: EntryExitMonitor,
        session_manager: SessionManager,
        dwell_tracker: DwellTracker,
        head_pose_estimator: HeadPoseEstimator,
        attention_classifier: AttentionClassifier,
        temporal_smoother: TemporalSmoother,
        region_manager: AttentionRegionManager,
        attention_tracker: AttentionTracker,
        visualizer: AttentionVisualizer,
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
        self.head_pose_estimator = head_pose_estimator
        self.attention_classifier = attention_classifier
        self.temporal_smoother = temporal_smoother
        self.region_manager = region_manager
        self.attention_tracker = attention_tracker
        self.visualizer = visualizer
        self.logger = logger or setup_logger("attention_video_processor")

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
            self.region_manager.scale_to_frame_size(self.width, self.height)

    def close(self) -> None:
        """Release video capture resources."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Video capture released.")

    def process_video_file(self) -> Dict:
        """Process video file through the full Phase 5 pipeline."""
        self.open()
        self.tracker.reset()

        ensure_directory(self.config.videos_dir)
        ensure_directory(self.config.reports_dir)
        ensure_directory(self.config.plots_dir)

        source_name = Path(self.source).stem
        output_video_path = self.config.videos_dir / f"{source_name}_attention_analysis.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_video_path), fourcc, self.fps, (self.width, self.height)
        )
        if not writer.isOpened():
            self.close()
            raise RuntimeError(f"Failed to create VideoWriter at: {output_video_path}")

        self.logger.info(f"Output video: {output_video_path}")
        self.logger.info("Starting attention analysis pipeline...")

        zone_names_map = {z.id: z.name for z in self.zone_manager.get_all_zones()}
        dwell_cfg = self.config.dwell_config
        mvmt_cfg = dwell_cfg.movement_config
        process_interval = self.config.attention_face_process_interval

        frame_number = 0
        total_inference_ms = 0.0
        total_tracking_ms = 0.0
        pipeline_start = time.perf_counter()
        previous_active_ids: Set[int] = set()

        # Cache last known head pose per track for skipped frames
        last_pose: Dict[int, HeadPoseResult] = {}
        last_direction: Dict[int, AttentionDirection] = {}
        last_confidence: Dict[int, float] = {}
        last_state: Dict[int, AttentionState] = {}
        last_target_name: Dict[int, Optional[str]] = {}
        last_target_id: Dict[int, Optional[str]] = {}
        last_target_type: Dict[int, Optional[str]] = {}

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                frame_number += 1
                timestamp = frame_number / self.fps if self.fps > 0 else 0.0

                # Phase 1: YOLOv8 Person Detection
                detections, inference_ms = self.detector.detect(frame)
                total_inference_ms += inference_ms

                # Phase 2: ByteTrack Tracking
                active_tracks, tracking_ms = self.tracker.update(
                    detections=detections, frame_number=frame_number, timestamp=timestamp
                )
                total_tracking_ms += tracking_ms

                current_active_ids: Set[int] = set()
                annotated = frame.copy()

                # Draw zones and attention regions
                if mvmt_cfg.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)
                if mvmt_cfg.entry_exit_enabled:
                    annotated = self.visualizer.draw_entry_exit_regions(annotated, self.zone_manager)

                annotated = self.visualizer.draw_attention_regions(
                    annotated, self.region_manager.get_all_regions()
                )

                # Track-level stats for HUD
                valid_head_poses = 0
                attention_targets = 0
                unknown_estimates = 0

                # Phase 3-5: Per-track processing
                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    current_active_ids.add(tid)

                    # Phase 3: Path/zone/entry-exit
                    if mvmt_cfg.path_tracking_enabled:
                        self.path_tracker.update(tid, frame_number, timestamp, cx, cy)

                    current_zone_ids = []
                    foot_x = cx
                    foot_y = int(track.bbox[3])
                    if mvmt_cfg.zone_tracking_enabled:
                        current_zone_ids = self.zone_tracker.update(
                            tid, frame_number, timestamp, foot_x, foot_y
                        )

                    if mvmt_cfg.entry_exit_enabled:
                        self.entry_exit_monitor.update(tid, frame_number, timestamp, foot_x, foot_y)

                    # Phase 4: Dwell-time
                    if dwell_cfg.dwell_time_enabled and mvmt_cfg.zone_tracking_enabled:
                        self.dwell_tracker.update(
                            track_id=tid, frame=frame_number, timestamp=timestamp,
                            current_zone_ids=current_zone_ids, zone_names=zone_names_map,
                            confidence=track.confidence,
                        )

                    # Phase 3: Session update
                    self.session_manager.update_session(tid, frame_number, timestamp, track.confidence)

                    # Phase 5: Head pose estimation (with interval skip)
                    should_process_face = (frame_number % process_interval == 0)

                    if should_process_face and self.config.attention_analysis_enabled:
                        pose = self.head_pose_estimator.estimate(frame, track.bbox)
                        last_pose[tid] = pose

                        if pose.face_detected:
                            valid_head_poses += 1
                            direction, state = self.attention_classifier.classify(
                                yaw=pose.yaw,
                                pitch=pose.pitch,
                                confidence=pose.confidence,
                                confidence_threshold=self.config.attention_confidence_threshold,
                            )

                            # Temporal smoothing
                            smoothed_dir, smoothed_conf = self.temporal_smoother.update(
                                tid, direction, pose.confidence
                            )

                            # Re-classify state after smoothing
                            if smoothed_dir == AttentionDirection.UNKNOWN:
                                smoothed_state = AttentionState.UNKNOWN
                            else:
                                smoothed_state = AttentionState.ATTENDING

                            # Attention target association
                            target = self.region_manager.find_attention_target(
                                head_x=pose.nose_point[0],
                                head_y=pose.nose_point[1],
                                yaw=pose.yaw,
                                pitch=pose.pitch,
                                max_distance=self.config.attention_max_target_distance,
                            )

                            t_id = target.id if target else None
                            t_name = target.name if target else None
                            t_type = target.type if target else None

                            if target:
                                attention_targets += 1
                            if smoothed_dir == AttentionDirection.UNKNOWN:
                                unknown_estimates += 1

                            # Cache
                            last_direction[tid] = smoothed_dir
                            last_confidence[tid] = smoothed_conf
                            last_state[tid] = smoothed_state
                            last_target_name[tid] = t_name
                            last_target_id[tid] = t_id
                            last_target_type[tid] = t_type

                        else:
                            unknown_estimates += 1
                            last_direction[tid] = AttentionDirection.UNKNOWN
                            last_confidence[tid] = 0.0
                            last_state[tid] = AttentionState.UNKNOWN
                            last_target_name[tid] = None
                            last_target_id[tid] = None
                            last_target_type[tid] = None

                    # Use cached values for attention tracking & visualization
                    cur_dir = last_direction.get(tid, AttentionDirection.UNKNOWN)
                    cur_conf = last_confidence.get(tid, 0.0)
                    cur_state = last_state.get(tid, AttentionState.UNKNOWN)
                    cur_t_name = last_target_name.get(tid)
                    cur_t_id = last_target_id.get(tid)
                    cur_t_type = last_target_type.get(tid)

                    # Attention event tracking
                    zone_id = current_zone_ids[0] if current_zone_ids else "unknown"
                    if self.config.attention_analysis_enabled:
                        self.attention_tracker.update(
                            track_id=tid,
                            frame=frame_number,
                            timestamp=timestamp,
                            target_id=cur_t_id,
                            target_name=cur_t_name,
                            target_type=cur_t_type,
                            direction=cur_dir,
                            confidence=cur_conf,
                            zone_id=zone_id,
                            state=cur_state,
                        )

                    # Visualization: path trail
                    if mvmt_cfg.path_tracking_enabled:
                        path = self.path_tracker.get_path(tid)
                        if path:
                            annotated = self.visualizer.draw_path(annotated, path, tid)

                    # Visualization: head pose arrow
                    cur_pose = last_pose.get(tid, NO_DETECTION)
                    annotated = self.visualizer.draw_head_pose(annotated, cur_pose, tid)

                    # Visualization: track box with attention info
                    zone_names_list = (
                        self.zone_tracker.get_current_zone_names(tid)
                        if mvmt_cfg.zone_tracking_enabled
                        else []
                    )
                    active_dt = (
                        self.dwell_tracker.get_active_dwell_times(tid, timestamp)
                        if dwell_cfg.dwell_time_enabled
                        else {}
                    )
                    annotated = self.visualizer.draw_track_with_attention(
                        annotated, track, zone_names_list,
                        cur_dir, cur_t_name, cur_conf, cur_state, active_dt,
                    )

                # Handle lost tracks
                lost_ids = previous_active_ids - current_active_ids
                for lost_id in lost_ids:
                    lost_ts = (frame_number - 1) / self.fps if self.fps > 0 else 0.0
                    if mvmt_cfg.entry_exit_enabled:
                        self.entry_exit_monitor.mark_track_lost(lost_id, frame_number - 1, lost_ts)
                    if mvmt_cfg.zone_tracking_enabled:
                        self.zone_tracker.close_track(lost_id, frame_number - 1, lost_ts)
                    if dwell_cfg.dwell_time_enabled:
                        self.dwell_tracker.handle_lost_track(lost_id, frame_number - 1, lost_ts)
                    if self.config.attention_analysis_enabled:
                        self.attention_tracker.handle_lost_track(lost_id, frame_number - 1, lost_ts)
                        self.temporal_smoother.reset(lost_id)

                    # Clean caches
                    last_pose.pop(lost_id, None)
                    last_direction.pop(lost_id, None)
                    last_confidence.pop(lost_id, None)
                    last_state.pop(lost_id, None)
                    last_target_name.pop(lost_id, None)
                    last_target_id.pop(lost_id, None)
                    last_target_type.pop(lost_id, None)

                previous_active_ids = current_active_ids

                # Draw HUD
                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                annotated = self.visualizer.draw_attention_hud(
                    frame=annotated,
                    frame_number=frame_number,
                    active_shoppers=len(active_tracks),
                    valid_head_poses=valid_head_poses,
                    attention_targets=attention_targets,
                    unknown_estimates=unknown_estimates,
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

                    self.logger.info(
                        f"Frame: {frame_number}{progress} | "
                        f"Active shoppers: {len(active_tracks)} | "
                        f"Valid head poses: {valid_head_poses} | "
                        f"Attention targets: {attention_targets} | "
                        f"Unknown estimates: {unknown_estimates}"
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

        # Close remaining events at video end
        self.dwell_tracker.close_remaining_visits(frame_number, final_timestamp, status="completed")
        self.attention_tracker.close_remaining_events(frame_number, final_timestamp)

        self.logger.info("Processing completed.")
        self.logger.info(f"Unique shoppers: {self.tracker.total_unique_tracks}")
        self.logger.info(f"Total attention events: {self.attention_tracker.total_events}")

        # Finalize Phase 3 sessions
        self.session_manager.finalize_all(
            path_tracker=self.path_tracker,
            zone_tracker=self.zone_tracker,
            entry_exit_monitor=self.entry_exit_monitor,
        )

        # Release head pose resources
        self.head_pose_estimator.close()

        return {
            "video_filename": Path(self.source).name,
            "video_path": str(Path(self.source).resolve()),
            "video_duration_sec": round(self.duration_sec, 2),
            "video_resolution": f"{self.width}x{self.height}",
            "video_fps": round(self.fps, 2),
            "total_frames_processed": frame_number,
            "total_unique_shoppers": self.tracker.total_unique_tracks,
            "total_attention_events": self.attention_tracker.total_events,
            "average_yolo_inference_ms": round(
                total_inference_ms / frame_number if frame_number > 0 else 0.0, 2
            ),
            "average_tracking_ms": round(
                total_tracking_ms / frame_number if frame_number > 0 else 0.0, 2
            ),
            "total_pipeline_time_sec": round(pipeline_elapsed, 2),
            "processing_fps": round(
                frame_number / pipeline_elapsed if pipeline_elapsed > 0 else 0.0, 2
            ),
            "device": self.detector.device,
            "model": str(self.detector.model_path),
            "output_video": str(output_video_path),
            "attention_confidence_threshold": self.config.attention_confidence_threshold,
            "attention_smoothing_window": self.config.attention_smoothing_window,
            "face_process_interval": self.config.attention_face_process_interval,
        }

    def process_webcam(self) -> None:
        """Process live webcam feed with attention HUD overlays. Press 'q' to quit."""
        self.open()
        self.tracker.reset()

        self.logger.info("Starting live attention analysis from webcam...")
        self.logger.info("Press 'q' to quit.")

        zone_names_map = {z.id: z.name for z in self.zone_manager.get_all_zones()}
        dwell_cfg = self.config.dwell_config
        mvmt_cfg = dwell_cfg.movement_config
        process_interval = self.config.attention_face_process_interval

        frame_number = 0
        pipeline_start = time.perf_counter()
        previous_active_ids: Set[int] = set()

        last_pose: Dict[int, HeadPoseResult] = {}
        last_direction: Dict[int, AttentionDirection] = {}
        last_confidence: Dict[int, float] = {}
        last_state: Dict[int, AttentionState] = {}
        last_target_name: Dict[int, Optional[str]] = {}

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

                if mvmt_cfg.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)

                annotated = self.visualizer.draw_attention_regions(
                    annotated, self.region_manager.get_all_regions()
                )

                valid_hp = 0
                attn_tgt = 0
                unknown_est = 0

                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    current_active_ids.add(tid)

                    if mvmt_cfg.zone_tracking_enabled:
                        self.zone_tracker.update(tid, frame_number, timestamp, cx, cy)

                    should_process = (frame_number % process_interval == 0)
                    if should_process and self.config.attention_analysis_enabled:
                        pose = self.head_pose_estimator.estimate(frame, track.bbox)
                        last_pose[tid] = pose
                        if pose.face_detected:
                            valid_hp += 1
                            d, s = self.attention_classifier.classify(
                                pose.yaw, pose.pitch, pose.confidence,
                                self.config.attention_confidence_threshold,
                            )
                            sd, sc = self.temporal_smoother.update(tid, d, pose.confidence)
                            last_direction[tid] = sd
                            last_confidence[tid] = sc
                            last_state[tid] = AttentionState.ATTENDING if sd != AttentionDirection.UNKNOWN else AttentionState.UNKNOWN
                            target = self.region_manager.find_attention_target(
                                pose.nose_point[0], pose.nose_point[1],
                                pose.yaw, pose.pitch, self.config.attention_max_target_distance,
                            )
                            last_target_name[tid] = target.name if target else None
                            if target:
                                attn_tgt += 1
                        else:
                            unknown_est += 1
                            last_direction[tid] = AttentionDirection.UNKNOWN
                            last_confidence[tid] = 0.0
                            last_state[tid] = AttentionState.UNKNOWN
                            last_target_name[tid] = None

                    zone_names_list = self.zone_tracker.get_current_zone_names(tid) if mvmt_cfg.zone_tracking_enabled else []
                    cur_pose = last_pose.get(tid, NO_DETECTION)
                    annotated = self.visualizer.draw_head_pose(annotated, cur_pose, tid)
                    annotated = self.visualizer.draw_track_with_attention(
                        annotated, track, zone_names_list,
                        last_direction.get(tid, AttentionDirection.UNKNOWN),
                        last_target_name.get(tid),
                        last_confidence.get(tid, 0.0),
                        last_state.get(tid, AttentionState.UNKNOWN),
                        {},
                    )

                lost_ids = previous_active_ids - current_active_ids
                for lost_id in lost_ids:
                    self.temporal_smoother.reset(lost_id)
                    last_pose.pop(lost_id, None)
                    last_direction.pop(lost_id, None)
                    last_confidence.pop(lost_id, None)
                    last_state.pop(lost_id, None)
                    last_target_name.pop(lost_id, None)

                previous_active_ids = current_active_ids

                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0
                annotated = self.visualizer.draw_attention_hud(
                    annotated, frame_number, len(active_tracks),
                    valid_hp, attn_tgt, unknown_est,
                    current_fps, inference_ms, tracking_ms,
                )

                cv2.imshow("Attention Analysis — Press 'q' to quit", annotated)
                if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
                    self.logger.info("Quit signal received.")
                    break

        except KeyboardInterrupt:
            self.logger.info("Webcam session interrupted.")
        finally:
            cv2.destroyAllWindows()
            self.close()
            self.head_pose_estimator.close()

        self.logger.info(f"Webcam session ended. Frames: {frame_number}")
