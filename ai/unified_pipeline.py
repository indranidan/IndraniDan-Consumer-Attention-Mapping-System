"""
Module 3 — Unified Single-Pass AI Pipeline
===========================================
Executes Person Detection (Phase 1), Multi-Person ByteTrack Tracking (Phase 2),
Movement Analysis (Phase 3), Dwell-Time Analytics (Phase 4), and Attention/Gaze
Analysis (Phase 5) in a SINGLE VIDEO PROCESSING PASS.

This eliminates:
- 5x redundant video decoding
- 5x redundant YOLOv8 model loading
- 5x redundant YOLOv8 object detection inference
- 4x redundant ByteTrack multi-person tracking
- 3x redundant Zone & Session tracking

After the single video pass, reports and visual plots for Phases 1-5 are generated,
followed by Phase 6 attention report aggregation.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

# Ensure project root is in sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent if _SCRIPT_DIR.name == "ai" else _SCRIPT_DIR
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.logger import setup_logger
from ai.utils import ensure_directory, print_banner
from ai.pipeline_profiler import PipelineProfiler

# Configuration loaders
from ai.attention_analysis.config import load_attention_analysis_config, AttentionAnalysisConfig

# Module 3 Components
from ai.person_detection.detector import PersonDetector, Detection
from ai.person_tracking.tracker import PersonTracker, TrackData, TrackInfo
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.traffic_analyzer import TrafficAnalyzer

from ai.dwell_time_analysis.dwell_tracker import DwellTracker
from ai.dwell_time_analysis.dwell_aggregator import DwellAggregator
from ai.dwell_time_analysis.plots import DwellPlotGenerator

from ai.attention_analysis.head_pose_estimator import HeadPoseEstimator, HeadPoseResult, NO_DETECTION
from ai.attention_analysis.attention_classifier import AttentionClassifier, AttentionDirection, AttentionState
from ai.attention_analysis.temporal_smoother import TemporalSmoother
from ai.attention_analysis.attention_region_manager import AttentionRegionManager
from ai.attention_analysis.attention_tracker import AttentionTracker
from ai.attention_analysis.visualizer import AttentionVisualizer
from ai.attention_analysis.plots import AttentionPlotGenerator

# Report Generators
from ai.person_detection.report import ReportGenerator as Phase1ReportGenerator
from ai.person_tracking.report import TrackingReportGenerator as Phase2ReportGenerator
from ai.movement_analysis.report import MovementReportGenerator as Phase3ReportGenerator
from ai.dwell_time_analysis.report import DwellReportGenerator as Phase4ReportGenerator
from ai.attention_analysis.report import AttentionReportGenerator as Phase5ReportGenerator
from ai.generate_attention_report import main as run_phase6_report


class UnifiedPipelineProcessor:
    """Executes single-pass video processing across all Module 3 AI phases."""

    def __init__(self, config: AttentionAnalysisConfig, source: str, logger: Optional[logging.Logger] = None):
        self.config = config
        self.source = source
        self.logger = logger or setup_logger("unified_pipeline")
        self.profiler = PipelineProfiler(logger=self.logger)

        # Base output directory resolution
        raw_base = os.getenv("AI_JOB_OUTPUT_PATH") or os.getenv("OUTPUT_BASE_PATH")
        if not raw_base:
            attn_env = os.getenv("ATTENTION_OUTPUT_PATH", "outputs/module3")
            attn_path = Path(attn_env)
            if attn_path.name == "phase5":
                raw_base = str(attn_path.parent)
            else:
                raw_base = str(attn_path)
        
        self.output_dir = Path(raw_base)

        p1_env = os.getenv("PHASE1_OUTPUT_PATH")
        self.p1_dir = Path(p1_env).parent if p1_env and Path(p1_env).name == "reports" else (Path(p1_env) if p1_env else self.output_dir / "phase1")

        p2_env = os.getenv("PHASE2_OUTPUT_PATH")
        self.p2_dir = Path(p2_env).parent if p2_env and Path(p2_env).name == "reports" else (Path(p2_env) if p2_env else self.output_dir / "phase2")

        p3_env = os.getenv("MOVEMENT_OUTPUT_PATH") or os.getenv("PHASE3_OUTPUT_PATH")
        if p3_env:
            p3_p = Path(p3_env)
            self.p3_dir = p3_p.parent if p3_p.name == "reports" else p3_p
        else:
            self.p3_dir = self.output_dir / "phase3"

        p4_env = os.getenv("DWELL_OUTPUT_PATH") or os.getenv("PHASE4_OUTPUT_PATH")
        if p4_env:
            p4_p = Path(p4_env)
            self.p4_dir = p4_p.parent if p4_p.name == "reports" else p4_p
        else:
            self.p4_dir = self.output_dir / "phase4"

        p5_env = os.getenv("ATTENTION_OUTPUT_PATH") or os.getenv("PHASE5_OUTPUT_PATH")
        if p5_env:
            p5_p = Path(p5_env)
            if p5_p.name == "reports":
                self.p5_dir = p5_p.parent
            elif p5_p.name == "phase5":
                self.p5_dir = p5_p
            else:
                self.p5_dir = p5_p / "phase5" if not p5_p.name.startswith("phase") else p5_p
        else:
            self.p5_dir = self.output_dir / "phase5"

        for p_dir in [self.p1_dir, self.p2_dir, self.p3_dir, self.p4_dir, self.p5_dir]:
            ensure_directory(p_dir / "reports")
            ensure_directory(p_dir / "videos")
            if p_dir in [self.p3_dir, self.p4_dir, self.p5_dir]:
                ensure_directory(p_dir / "plots")

        # Initialize AI components
        self.logger.info("Initializing unified AI pipeline components...")
        
        dwell_cfg = self.config.dwell_config
        mvmt_cfg = dwell_cfg.movement_config
        tracking_cfg = mvmt_cfg.tracking_config
        detection_cfg = tracking_cfg.detection_config

        self.detector = PersonDetector(detection_cfg, logger=self.logger)
        self.tracker = PersonTracker(tracking_cfg, logger=self.logger)
        self.zone_manager = ZoneManager(mvmt_cfg.zone_config_path, logger=self.logger)
        self.path_tracker = PathTracker(history_length=mvmt_cfg.path_history_length)
        self.zone_tracker = ZoneTracker(zone_manager=self.zone_manager, logger=self.logger)
        self.entry_exit_monitor = EntryExitMonitor(zone_manager=self.zone_manager, logger=self.logger)
        self.session_manager = SessionManager(logger=self.logger)
        self.dwell_tracker = DwellTracker(gap_tolerance=dwell_cfg.dwell_track_gap_tolerance, logger=self.logger)

        self.head_pose_estimator = HeadPoseEstimator(
            min_detection_confidence=self.config.attention_confidence_threshold,
            logger=self.logger,
        )
        self.attention_classifier = AttentionClassifier()
        self.temporal_smoother = TemporalSmoother(window_size=self.config.attention_smoothing_window)
        self.region_manager = AttentionRegionManager(config_path=self.config.attention_regions_path, logger=self.logger)
        self.attention_tracker = AttentionTracker(min_duration=self.config.attention_min_duration, logger=self.logger)
        self.visualizer = AttentionVisualizer()

        # Video metadata
        self.cap: Optional[cv2.VideoCapture] = None
        self.width = 0
        self.height = 0
        self.fps = 0.0
        self.total_frames = 0
        self.duration_sec = 0.0

    def process(self) -> None:
        """Run the single-pass video processing loop and generate all phase reports."""
        self.profiler.start_pipeline()
        
        # 1. Open Video
        t0 = time.perf_counter()
        source_str = str(self.source)
        if source_str.isdigit():
            self.cap = cv2.VideoCapture(int(source_str))
        else:
            self.cap = cv2.VideoCapture(source_str)

        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {self.source}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        if self.fps <= 0 or np.isnan(self.fps):
            self.fps = 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.total_frames < 0:
            self.total_frames = 0
        self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0.0
        self.profiler.record_phase("Video Initialization", (time.perf_counter() - t0) * 1000)

        source_name = Path(source_str).stem
        
        # Comprehensive output video path (Phase 5 video style with all overlays)
        p5_video_path = self.config.videos_dir / f"{source_name}_attention_analysis.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(p5_video_path), fourcc, self.fps, (self.width, self.height))

        self.logger.info(f"Video Source : {self.source} ({self.width}x{self.height} @ {self.fps:.1f} FPS, {self.total_frames} frames)")
        self.logger.info(f"Primary Output Video: {p5_video_path}")

        # Tracking state accumulators across phases
        zone_names_map = {z.id: z.name for z in self.zone_manager.get_all_zones()}
        process_interval = self.config.attention_face_process_interval
        
        # Check for global frame skip setting (default 1 = no skip)
        ai_frame_skip = int(os.getenv("AI_FRAME_SKIP", "1"))
        if ai_frame_skip < 1:
            ai_frame_skip = 1

        frame_number = 0
        previous_active_ids: Set[int] = set()

        # Phase 1 & 2 tracking statistics
        p1_total_detections = 0
        p1_frames_with_persons = 0
        p1_confidence_sum = 0.0
        frame_tracking_records: List[Dict] = []

        # Face pose cache for skipped face frames
        last_pose: Dict[int, HeadPoseResult] = {}
        last_direction: Dict[int, AttentionDirection] = {}
        last_confidence: Dict[int, float] = {}
        last_state: Dict[int, AttentionState] = {}
        last_target_name: Dict[int, Optional[str]] = {}
        last_target_id: Dict[int, Optional[str]] = {}
        last_target_type: Dict[int, Optional[str]] = {}

        mvmt_cfg = self.config.dwell_config.movement_config
        dwell_cfg = self.config.dwell_config

        last_active_tracks: List[TrackData] = []
        last_detections: List[Detection] = []

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                frame_number += 1
                self.profiler.total_frames = frame_number
                timestamp = frame_number / self.fps if self.fps > 0 else 0.0

                # Determine if we execute YOLO + ByteTrack on this frame or reuse last tracks
                should_run_detection = ((frame_number - 1) % ai_frame_skip == 0) or (frame_number == 1)

                if should_run_detection:
                    # Phase 1: Detection
                    t_det = time.perf_counter()
                    detections, inference_ms = self.detector.detect(frame)
                    self.profiler.record_phase("Phase 1: Person Detection", inference_ms)
                    last_detections = detections

                    # Phase 2: ByteTrack
                    t_trk = time.perf_counter()
                    active_tracks, tracking_ms = self.tracker.update(
                        detections=detections, frame_number=frame_number, timestamp=timestamp
                    )
                    self.profiler.record_phase("Phase 2: ByteTrack", tracking_ms)
                    last_active_tracks = active_tracks
                else:
                    detections = last_detections
                    active_tracks = last_active_tracks

                # Update Phase 1 & 2 statistics
                num_dets = len(detections)
                p1_total_detections += num_dets
                if num_dets > 0:
                    p1_frames_with_persons += 1
                    p1_confidence_sum += sum(d.confidence for d in detections)

                # Record frame-level track positions for tracks.json
                frame_rec = {
                    "frame": frame_number,
                    "timestamp": round(timestamp, 3),
                    "active_tracks_count": len(active_tracks),
                    "tracks": [
                        {
                            "track_id": trk.track_id,
                            "bbox": list(trk.bbox),
                            "confidence": round(trk.confidence, 4),
                            "center": list(trk.center),
                        }
                        for trk in active_tracks
                    ],
                }
                frame_tracking_records.append(frame_rec)

                current_active_ids: Set[int] = set()
                annotated = frame.copy()

                # Visual overlay: Zones & Entry/Exit
                t_vis = time.perf_counter()
                if mvmt_cfg.zone_tracking_enabled:
                    annotated = self.visualizer.draw_zones(annotated, self.zone_manager)
                if mvmt_cfg.entry_exit_enabled:
                    annotated = self.visualizer.draw_entry_exit_regions(annotated, self.zone_manager)
                annotated = self.visualizer.draw_attention_regions(
                    annotated, self.region_manager.get_all_regions()
                )

                # Phase 3-5 Per-Track Analytics
                t_analytics = time.perf_counter()
                for track in active_tracks:
                    tid = track.track_id
                    cx, cy = track.center
                    current_active_ids.add(tid)

                    # Phase 3: Path / Zone / Entry-Exit
                    if mvmt_cfg.path_tracking_enabled:
                        self.path_tracker.update(tid, frame_number, timestamp, cx, cy)

                    current_zone_ids = []
                    if mvmt_cfg.zone_tracking_enabled:
                        current_zone_ids = self.zone_tracker.update(tid, frame_number, timestamp, cx, cy)

                    if mvmt_cfg.entry_exit_enabled:
                        self.entry_exit_monitor.update(tid, frame_number, timestamp, cx, cy)

                    # Phase 4: Dwell-Time
                    if dwell_cfg.dwell_time_enabled and mvmt_cfg.zone_tracking_enabled:
                        self.dwell_tracker.update(
                            track_id=tid,
                            frame=frame_number,
                            timestamp=timestamp,
                            current_zone_ids=current_zone_ids,
                            zone_names=zone_names_map,
                            confidence=track.confidence,
                        )

                    # Phase 3: Session Manager
                    self.session_manager.update_session(tid, frame_number, timestamp, track.confidence)

                    # Phase 5: Attention / Head Pose Estimation
                    should_process_face = (frame_number % process_interval == 0)

                    if should_process_face and self.config.attention_analysis_enabled:
                        pose = self.head_pose_estimator.estimate(frame, track.bbox)
                        last_pose[tid] = pose

                        if pose.face_detected:
                            direction, state = self.attention_classifier.classify(
                                yaw=pose.yaw,
                                pitch=pose.pitch,
                                confidence=pose.confidence,
                                confidence_threshold=self.config.attention_confidence_threshold,
                            )
                            smoothed_dir, smoothed_conf = self.temporal_smoother.update(
                                tid, direction, pose.confidence
                            )
                            smoothed_state = AttentionState.UNKNOWN if smoothed_dir == AttentionDirection.UNKNOWN else AttentionState.ATTENDING

                            target = self.region_manager.find_attention_target(
                                head_x=pose.nose_point[0],
                                head_y=pose.nose_point[1],
                                yaw=pose.yaw,
                                pitch=pose.pitch,
                                max_distance=self.config.attention_max_target_distance,
                            )

                            last_direction[tid] = smoothed_dir
                            last_confidence[tid] = smoothed_conf
                            last_state[tid] = smoothed_state
                            last_target_name[tid] = target.name if target else None
                            last_target_id[tid] = target.id if target else None
                            last_target_type[tid] = target.type if target else None
                        else:
                            last_direction[tid] = AttentionDirection.UNKNOWN
                            last_confidence[tid] = 0.0
                            last_state[tid] = AttentionState.UNKNOWN
                            last_target_name[tid] = None
                            last_target_id[tid] = None
                            last_target_type[tid] = None

                    # Retrieve active attention info
                    cur_dir = last_direction.get(tid, AttentionDirection.UNKNOWN)
                    cur_conf = last_confidence.get(tid, 0.0)
                    cur_state = last_state.get(tid, AttentionState.UNKNOWN)
                    cur_t_name = last_target_name.get(tid)
                    cur_t_id = last_target_id.get(tid)
                    cur_t_type = last_target_type.get(tid)

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

                    # Draw per-track visual elements
                    if mvmt_cfg.path_tracking_enabled:
                        path_pts = self.path_tracker.get_path(tid)
                        if path_pts:
                            annotated = self.visualizer.draw_path(annotated, path_pts, tid)

                    cur_pose = last_pose.get(tid, NO_DETECTION)
                    annotated = self.visualizer.draw_head_pose(annotated, cur_pose, tid)

                    zone_names_list = self.zone_tracker.get_current_zone_names(tid) if mvmt_cfg.zone_tracking_enabled else []
                    active_dt = self.dwell_tracker.get_active_dwell_times(tid, timestamp) if dwell_cfg.dwell_time_enabled else {}
                    
                    annotated = self.visualizer.draw_track_with_attention(
                        annotated, track, zone_names_list,
                        cur_dir, cur_t_name, cur_conf, cur_state, active_dt
                    )

                self.profiler.record_phase("Phase 3-5 Analytics", (time.perf_counter() - t_analytics) * 1000)

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

                previous_active_ids = current_active_ids

                # Draw HUD and write frame
                annotated = self.visualizer.draw_attention_hud(
                    annotated,
                    frame_number=frame_number,
                    active_shoppers=len(active_tracks),
                    valid_head_poses=sum(1 for p in last_pose.values() if p.face_detected),
                    attention_targets=sum(1 for t in last_target_name.values() if t is not None),
                    unknown_estimates=sum(1 for d in last_direction.values() if d == AttentionDirection.UNKNOWN),
                    fps=self.profiler.total_frames / self.profiler.total_duration_sec if self.profiler.total_duration_sec > 0 else 0.0,
                    inference_ms=self.profiler.phase_times_ms.get("Phase 1: Person Detection", 0.0) / frame_number if frame_number > 0 else 0.0,
                    tracking_ms=self.profiler.phase_times_ms.get("Phase 2: ByteTrack", 0.0) / frame_number if frame_number > 0 else 0.0,
                )

                writer.write(annotated)
                self.profiler.record_phase("Frame Encoding & Overlay", (time.perf_counter() - t_vis) * 1000)

                if frame_number % 50 == 0 or frame_number == self.total_frames:
                    eff_fps = frame_number / self.profiler.total_duration_sec if self.profiler.total_duration_sec > 0 else 0.0
                    self.logger.info(
                        f"Frame {frame_number}/{self.total_frames} ({frame_number/self.total_frames*100:.1f}%) | "
                        f"Active Tracks: {len(active_tracks)} | Speed: {eff_fps:.1f} FPS"
                    )

        finally:
            if self.cap:
                self.cap.release()
            writer.release()
            self.head_pose_estimator.close()

        # Finalize processing state across modules
        final_ts = frame_number / self.fps if self.fps > 0 else 0.0
        self.dwell_tracker.close_remaining_visits(frame_number, final_ts, status="completed")
        self.attention_tracker.close_remaining_events(frame_number, final_ts)
        self.session_manager.finalize_all(self.path_tracker, self.zone_tracker, self.entry_exit_monitor)

        # Complete pipeline profiling
        total_pipeline_time_sec = self.profiler.stop_pipeline()
        effective_fps = frame_number / total_pipeline_time_sec if total_pipeline_time_sec > 0 else 0.0

        # Generate Phase 1-5 video files (symlink / copy / alias to primary video to save 4x encode overhead)
        self._sync_output_videos(p5_video_path)

        # ──────────────────────────────────────────────────────────
        # Generate Reports for Phases 1–5
        # ──────────────────────────────────────────────────────────
        self.logger.info("Generating reports for Phase 1 to Phase 5...")

        # Phase 1 Report
        p1_avg_inf = (self.profiler.phase_times_ms["Phase 1: Person Detection"] / frame_number) if frame_number > 0 else 0.0
        p1_avg_conf = (p1_confidence_sum / p1_total_detections) if p1_total_detections > 0 else 0.0
        p1_stats = {
            "video_filename": Path(source_str).name,
            "video_path": source_str,
            "video_resolution": f"{self.width}x{self.height}",
            "video_fps": self.fps,
            "video_duration_sec": round(self.duration_sec, 2),
            "total_frames_processed": frame_number,
            "total_frames_with_persons": p1_frames_with_persons,
            "total_person_detections": p1_total_detections,
            "average_confidence": round(p1_avg_conf, 4),
            "average_inference_time_ms": round(p1_avg_inf, 2),
            "total_pipeline_time_sec": round(total_pipeline_time_sec, 2),
            "effective_fps": round(effective_fps, 2),
            "device": "cpu",
            "model": str(self.config.dwell_config.movement_config.tracking_config.detection_config.person_model_path),
            "confidence_threshold": self.config.dwell_config.movement_config.tracking_config.detection_config.confidence_threshold,
            "image_size": self.config.dwell_config.movement_config.tracking_config.detection_config.image_size,
            "save_frames": False,
            "output_video": str(self.p1_dir / "videos" / f"{source_name}_person_detection.mp4"),
        }
        Phase1ReportGenerator(self.p1_dir / "reports", logger=self.logger).generate(p1_stats)

        # Phase 2 Report
        p2_avg_trk = (self.profiler.phase_times_ms["Phase 2: ByteTrack"] / frame_number) if frame_number > 0 else 0.0
        p2_stats = {
            "video_filename": Path(source_str).name,
            "video_resolution": f"{self.width}x{self.height}",
            "video_duration_sec": round(self.duration_sec, 2),
            "video_fps": self.fps,
            "total_frames_processed": frame_number,
            "total_person_detections": p1_total_detections,
            "total_unique_tracking_ids": self.tracker.total_unique_tracks,
            "max_simultaneous_tracked_people": self.tracker.max_simultaneous_tracks,
            "average_active_tracks": round(self.tracker.average_active_tracks, 2),
            "average_tracking_confidence": round(p1_avg_conf, 4),
            "average_yolo_inference_time_ms": round(p1_avg_inf, 2),
            "average_bytetrack_time_ms": round(p2_avg_trk, 2),
            "processing_fps": round(effective_fps, 2),
            "device": "cpu",
            "model": str(self.config.dwell_config.movement_config.tracking_config.detection_config.person_model_path),
            "tracker": "ByteTrack",
            "track_high_threshold": self.config.dwell_config.movement_config.tracking_config.track_high_threshold,
            "track_low_threshold": self.config.dwell_config.movement_config.tracking_config.track_low_threshold,
            "new_track_threshold": self.config.dwell_config.movement_config.tracking_config.new_track_threshold,
            "track_buffer": self.config.dwell_config.movement_config.tracking_config.track_buffer,
            "match_threshold": self.config.dwell_config.movement_config.tracking_config.match_threshold,
            "output_video": str(self.p2_dir / "videos" / f"{source_name}_person_tracking.mp4"),
        }
        Phase2ReportGenerator(self.p2_dir / "reports", logger=self.logger).generate(
            p2_stats, self.tracker.track_history, frame_tracking_records
        )

        # Phase 3 Report
        self.traffic_analyzer = TrafficAnalyzer(
            zone_manager=self.zone_manager,
            zone_tracker=self.zone_tracker,
            entry_exit_monitor=self.entry_exit_monitor,
            session_manager=self.session_manager,
            video_fps=self.fps,
            logger=self.logger,
        )
        traffic_stats = self.traffic_analyzer.generate_stats()
        p3_stats = {
            "video_filename": Path(source_str).name,
            "video_resolution": f"{self.width}x{self.height}",
            "video_duration_sec": round(self.duration_sec, 2),
            "video_fps": self.fps,
            "total_frames_processed": frame_number,
            "processing_fps": round(effective_fps, 2),
            "average_yolo_inference_ms": round(p1_avg_inf, 2),
            "average_tracking_ms": round(p2_avg_trk, 2),
            "total_pipeline_time_sec": round(total_pipeline_time_sec, 2),
            "device": "cpu",
            "model": str(self.config.dwell_config.movement_config.tracking_config.detection_config.person_model_path),
            "tracker": "ByteTrack",
            "total_unique_shoppers": self.tracker.total_unique_tracks,
            "total_entries": self.entry_exit_monitor.total_entries,
            "total_exits": self.entry_exit_monitor.total_exits,
            "total_track_lost": self.entry_exit_monitor.total_track_lost,
            "max_simultaneous_shoppers": self.tracker.max_simultaneous_tracks,
            "average_active_shoppers": round(self.tracker.average_active_tracks, 2),
            "traffic_stats": traffic_stats,
            "output_video": str(self.p3_dir / "videos" / f"{source_name}_movement_analysis.mp4"),
        }
        Phase3ReportGenerator(self.p3_dir / "reports", logger=self.logger).generate(
            p3_stats, self.session_manager, self.path_tracker, self.zone_tracker
        )

        # Phase 4 Report & Plots
        dwell_aggregator = DwellAggregator(logger=self.logger)
        zone_summaries = dwell_aggregator.aggregate_zones(self.dwell_tracker, self.zone_manager)
        shopper_summaries = dwell_aggregator.aggregate_shoppers(self.dwell_tracker, self.session_manager)
        dwell_distribution = dwell_aggregator.compute_distribution(self.dwell_tracker, dwell_cfg.dwell_distribution_buckets)

        p4_stats = {
            **p3_stats,
            "track_buffer": self.config.dwell_config.movement_config.tracking_config.track_buffer,
            "gap_tolerance": dwell_cfg.dwell_track_gap_tolerance,
            "output_video": str(self.p4_dir / "videos" / f"{source_name}_dwell_analysis.mp4"),
        }
        Phase4ReportGenerator(self.p4_dir / "reports", logger=self.logger).generate(
            p4_stats, self.dwell_tracker, zone_summaries, shopper_summaries, dwell_distribution, self.session_manager
        )
        DwellPlotGenerator(self.p4_dir / "plots", logger=self.logger).generate_all(
            zone_summaries, dwell_distribution
        )

        # Phase 5 Report & Plots
        p5_stats = {
            "video_filename": Path(source_str).name,
            "video_resolution": f"{self.width}x{self.height}",
            "video_duration_sec": round(self.duration_sec, 2),
            "total_frames_processed": frame_number,
            "processing_fps": round(effective_fps, 2),
            "device": "cpu",
            "total_unique_shoppers": self.tracker.total_unique_tracks,
            "output_video": str(p5_video_path),
        }
        p5_report_gen = Phase5ReportGenerator(self.p5_dir / "reports", logger=self.logger)
        p5_report_gen.generate(
            p5_stats, self.attention_tracker, self.region_manager, self.session_manager
        )

        all_events = self.attention_tracker.get_all_events()
        target_summaries = p5_report_gen._compute_target_summaries(all_events, self.region_manager)
        AttentionPlotGenerator(self.p5_dir / "plots", logger=self.logger).generate_all(
            all_events, target_summaries
        )

        self.logger.info("All reports and visualizations for Phases 1-5 generated successfully.")

        # Print performance profiling summary
        self.profiler.print_summary(video_fps=self.fps)

        # ──────────────────────────────────────────────────────────
        # Phase 6: Attention Reports & Analytics Aggregation
        # ──────────────────────────────────────────────────────────
        self.logger.info("Executing Phase 6: Attention Report Generator...")
        run_phase6_report()
        self.logger.info("Module 3 Unified AI Pipeline Execution Completed Successfully!")

    def _sync_output_videos(self, primary_video_path: Path) -> None:
        """Create copies/links of primary annotated video for Phase 1-4 output folders."""
        source_name = primary_video_path.name.replace("_attention_analysis.mp4", "")
        p1_vid = self.p1_dir / "videos" / f"{source_name}_person_detection.mp4"
        p2_vid = self.p2_dir / "videos" / f"{source_name}_person_tracking.mp4"
        p3_vid = self.p3_dir / "videos" / f"{source_name}_movement_analysis.mp4"
        p4_vid = self.p4_dir / "videos" / f"{source_name}_dwell_analysis.mp4"

        for target in [p1_vid, p2_vid, p3_vid, p4_vid]:
            try:
                if target.exists():
                    target.unlink()
                # Use hard link if available, fallback to copy
                try:
                    os.link(str(primary_video_path), str(target))
                except OSError:
                    import shutil
                    shutil.copy2(str(primary_video_path), str(target))
            except Exception as exc:
                self.logger.warning(f"Could not link video to {target}: {exc}")


def run_unified_pipeline(source: str) -> None:
    """Entry point to run the unified single-pass AI pipeline."""
    print_banner("INDRANI CONSUMER ATTENTION MAPPING SYSTEM\nModule 3 — Unified Single-Pass AI Pipeline")
    config = load_attention_analysis_config()
    processor = UnifiedPipelineProcessor(config=config, source=source)
    processor.process()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Unified Single-Pass AI Pipeline")
    parser.add_argument("--source", type=str, default="ai/video.mp4", help="Video source file or camera index")
    args = parser.parse_args()
    run_unified_pipeline(args.source)
