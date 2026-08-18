"""
Person Tracking — Video Processor
====================================
Manages video capture (file or webcam), coordinates YOLOv8 detection
and ByteTrack multi-person tracking, renders annotated output video,
and records detailed frame-level tracking statistics.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.logger import setup_logger
from ai.person_detection.detector import PersonDetector
from ai.person_tracking.config import PersonTrackingConfig
from ai.person_tracking.tracker import PersonTracker
from ai.person_tracking.visualizer import TrackVisualizer
from ai.utils import ensure_directory


class TrackingVideoProcessor:
    """
    Manages OpenCV video capture, frame processing loop through YOLOv8
    and ByteTrack, annotated output generation, and session statistics.
    """

    _LOG_INTERVAL = 50

    def __init__(
        self,
        source: str,
        config: PersonTrackingConfig,
        detector: PersonDetector,
        tracker: PersonTracker,
        visualizer: TrackVisualizer,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the tracking video processor.

        Parameters
        ----------
        source : str
            Path to video file, or webcam index string (e.g., "0").
        config : PersonTrackingConfig
            Pipeline configuration.
        detector : PersonDetector
            Initialized YOLOv8 person detector (Phase 1).
        tracker : PersonTracker
            Initialized ByteTrack tracker.
        visualizer : TrackVisualizer
            Track visualization helper.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.source = source
        self.config = config
        self.detector = detector
        self.tracker = tracker
        self.visualizer = visualizer
        self.logger = logger or setup_logger("tracking_video_processor")

        # Determine source type
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

        # Frame-level tracking data for tracks.json
        self.frame_tracking_records: List[Dict] = []

    def open(self) -> None:
        """
        Open the video source using OpenCV.

        Raises
        ------
        FileNotFoundError
            If video file does not exist.
        RuntimeError
            If OpenCV fails to open the video stream or webcam.
        """
        if self.is_webcam:
            self.logger.info(f"Opening webcam (index {self.webcam_index})...")
            self.cap = cv2.VideoCapture(self.webcam_index)

            if not self.cap.isOpened():
                raise RuntimeError(
                    f"Cannot open webcam at index {self.webcam_index}.\n"
                    f"Verify webcam is connected and not locked by another application."
                )

            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = 0

            self.logger.info("Webcam opened successfully.")
            self.logger.info(f"Resolution: {self.width}x{self.height} | FPS: {self.fps:.1f}")

        else:
            video_path = Path(self.source)
            if not video_path.exists():
                raise FileNotFoundError(
                    f"Video file not found at: {video_path}\n"
                    f"Please check the path and try again."
                )
            if not video_path.is_file():
                raise ValueError(f"Specified path is not a file: {video_path}")

            self.logger.info(f"Opening video file: {video_path}")
            self.cap = cv2.VideoCapture(str(video_path))

            if not self.cap.isOpened():
                raise RuntimeError(
                    f"Cannot open video file: {video_path}\n"
                    f"File may be corrupted or in an unsupported codec format."
                )

            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0.0

            self.logger.info("Video file opened successfully.")
            self.logger.info(
                f"Resolution: {self.width}x{self.height} | FPS: {self.fps:.1f} | "
                f"Total Frames: {self.total_frames:,} | Duration: {self.duration_sec:.1f}s"
            )

    def close(self) -> None:
        """Release OpenCV video capture."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Video capture released.")

    def process_video_file(self) -> Tuple[Dict, List[Dict]]:
        """
        Process video file frame by frame: YOLOv8 -> ByteTrack -> Annotate -> Save.

        Returns
        -------
        Tuple[Dict, List[Dict]]
            Session statistics dictionary and frame-level tracking history list.
        """
        self.open()
        self.tracker.reset()
        self.frame_tracking_records.clear()

        # Create output directories
        ensure_directory(self.config.videos_dir)
        ensure_directory(self.config.reports_dir)
        if self.config.detection_config.save_frames:
            ensure_directory(self.config.frames_dir)

        # Output video file path
        source_name = Path(self.source).stem
        output_video_path = self.config.videos_dir / f"{source_name}_person_tracking.mp4"

        # Initialize VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_video_path), fourcc, self.fps, (self.width, self.height)
        )
        if not writer.isOpened():
            self.close()
            raise RuntimeError(
                f"Failed to create output VideoWriter at: {output_video_path}\n"
                f"Check directory permissions and disk space."
            )

        self.logger.info(f"Saving annotated video to: {output_video_path}")
        self.logger.info("Starting multi-person detection and ByteTrack tracking...")

        frame_number = 0
        total_detections_count = 0
        total_inference_time_ms = 0.0
        total_tracking_time_ms = 0.0
        pipeline_start = time.perf_counter()

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                frame_number += 1
                timestamp_sec = frame_number / self.fps if self.fps > 0 else 0.0
                frame_start = time.perf_counter()

                # Step 1: YOLOv8 Person Detection (Phase 1)
                detections, inference_ms = self.detector.detect(frame)
                total_detections_count += len(detections)
                total_inference_time_ms += inference_ms

                # Step 2: ByteTrack Multi-Person Tracking (Phase 2)
                active_tracks, tracking_ms = self.tracker.update(
                    detections=detections,
                    frame_number=frame_number,
                    timestamp=timestamp_sec,
                )
                total_tracking_time_ms += tracking_ms

                frame_total_ms = (time.perf_counter() - frame_start) * 1000

                # Step 3: Visual Annotation & HUD
                annotated = self.visualizer.annotate(
                    frame=frame,
                    active_tracks=active_tracks,
                    track_history=self.tracker.track_history,
                )

                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                annotated = self.visualizer.draw_hud(
                    frame=annotated,
                    frame_number=frame_number,
                    active_tracks_count=len(active_tracks),
                    detections_count=len(detections),
                    inference_time_ms=inference_ms,
                    tracking_time_ms=tracking_ms,
                    fps=current_fps,
                )

                # Step 4: Write frame to video
                writer.write(annotated)

                # Optional frame saving
                if self.config.detection_config.save_frames and len(active_tracks) > 0:
                    frame_path = self.config.frames_dir / f"frame_{frame_number:06d}.jpg"
                    cv2.imwrite(str(frame_path), annotated)

                # Step 5: Save structured frame-level tracking record
                frame_record = {
                    "frame": frame_number,
                    "timestamp": round(timestamp_sec, 3),
                    "active_tracks_count": len(active_tracks),
                    "detections_count": len(detections),
                    "inference_time_ms": round(inference_ms, 2),
                    "tracking_time_ms": round(tracking_ms, 2),
                    "tracks": [
                        {
                            "track_id": t.track_id,
                            "bbox": list(t.bbox),
                            "confidence": round(t.confidence, 4),
                            "center": list(t.center),
                        }
                        for t in active_tracks
                    ],
                }
                self.frame_tracking_records.append(frame_record)

                # Periodic logging
                if frame_number % self._LOG_INTERVAL == 0 or frame_number == 1:
                    progress_str = ""
                    if self.total_frames > 0:
                        pct = (frame_number / self.total_frames) * 100
                        progress_str = f" ({pct:.1f}%)"

                    self.logger.info(
                        f"Frame {frame_number}{progress_str} | "
                        f"Active tracks: {len(active_tracks)} | "
                        f"Detections: {len(detections)} | "
                        f"YOLO: {inference_ms:.1f}ms | "
                        f"ByteTrack: {tracking_ms:.1f}ms | "
                        f"FPS: {current_fps:.1f}"
                    )

        except KeyboardInterrupt:
            self.logger.warning("Tracking pipeline interrupted by user (Ctrl+C).")
        except MemoryError:
            self.logger.error("Out of memory error during frame processing.")
            raise
        finally:
            writer.release()
            self.close()

        pipeline_elapsed = time.perf_counter() - pipeline_start

        self.logger.info("Multi-person tracking completed.")
        self.logger.info(f"Unique persistent tracking IDs assigned: {self.tracker.total_unique_tracks}")

        # Compute summary statistics
        all_track_infos = list(self.tracker.track_history.values())
        avg_track_conf = (
            sum(t.average_confidence for t in all_track_infos) / len(all_track_infos)
            if all_track_infos
            else 0.0
        )

        session_stats = {
            "video_filename": Path(self.source).name,
            "video_path": str(Path(self.source).resolve()),
            "video_duration_sec": round(self.duration_sec, 2),
            "video_resolution": f"{self.width}x{self.height}",
            "video_fps": round(self.fps, 2),
            "total_frames_processed": frame_number,
            "total_unique_tracking_ids": self.tracker.total_unique_tracks,
            "max_simultaneous_tracked_people": self.tracker.max_simultaneous_tracks,
            "average_active_tracks": round(self.tracker.average_active_tracks, 2),
            "total_person_detections": total_detections_count,
            "average_yolo_inference_time_ms": round(
                total_inference_time_ms / frame_number if frame_number > 0 else 0.0, 2
            ),
            "average_bytetrack_time_ms": round(
                total_tracking_time_ms / frame_number if frame_number > 0 else 0.0, 2
            ),
            "average_tracking_confidence": round(avg_track_conf, 4),
            "total_pipeline_time_sec": round(pipeline_elapsed, 2),
            "processing_fps": round(frame_number / pipeline_elapsed if pipeline_elapsed > 0 else 0.0, 2),
            "device": self.detector.device,
            "model": str(self.detector.model_path),
            "tracker": "ByteTrack",
            "confidence_threshold": self.config.detection_config.confidence_threshold,
            "track_high_threshold": self.config.track_high_threshold,
            "track_low_threshold": self.config.track_low_threshold,
            "new_track_threshold": self.config.new_track_threshold,
            "track_buffer": self.config.track_buffer,
            "match_threshold": self.config.match_threshold,
            "output_video": str(output_video_path),
        }

        return session_stats, self.frame_tracking_records

    def process_webcam(self) -> None:
        """
        Process live webcam feed: read -> detect -> track -> annotate -> display.

        Press 'q' to quit.
        """
        self.open()
        self.tracker.reset()

        self.logger.info("Starting live multi-person tracking from webcam...")
        self.logger.info("Press 'q' to quit.")

        frame_number = 0
        pipeline_start = time.perf_counter()

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.warning("Failed to read frame from webcam.")
                    break

                frame_number += 1
                timestamp_sec = frame_number / self.fps if self.fps > 0 else 0.0

                # Detect and Track
                detections, inference_ms = self.detector.detect(frame)
                active_tracks, tracking_ms = self.tracker.update(
                    detections=detections,
                    frame_number=frame_number,
                    timestamp=timestamp_sec,
                )

                # Annotate and HUD
                annotated = self.visualizer.annotate(
                    frame=frame,
                    active_tracks=active_tracks,
                    track_history=self.tracker.track_history,
                )

                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0

                annotated = self.visualizer.draw_hud(
                    frame=annotated,
                    frame_number=frame_number,
                    active_tracks_count=len(active_tracks),
                    detections_count=len(detections),
                    inference_time_ms=inference_ms,
                    tracking_time_ms=tracking_ms,
                    fps=current_fps,
                )

                # Display
                cv2.imshow("Person Tracking (ByteTrack) — Press 'q' to quit", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    self.logger.info("Quit signal received.")
                    break

                if frame_number % self._LOG_INTERVAL == 0:
                    self.logger.info(
                        f"Frame {frame_number} | Active tracks: {len(active_tracks)} | "
                        f"FPS: {current_fps:.1f}"
                    )

        except KeyboardInterrupt:
            self.logger.info("Webcam session interrupted by user.")
        finally:
            cv2.destroyAllWindows()
            self.close()

        self.logger.info(f"Webcam session ended. Frames processed: {frame_number}")
