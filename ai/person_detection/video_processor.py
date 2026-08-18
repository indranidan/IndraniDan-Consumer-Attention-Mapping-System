"""
Person Detection — Video Processor
=====================================
Handles OpenCV video input (file or webcam), frame-by-frame processing
through the PersonDetector, annotated output writing, and statistics collection.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.person_detection.config import PersonDetectionConfig
from ai.person_detection.detector import Detection, PersonDetector
from ai.logger import setup_logger
from ai.utils import ensure_directory


# ---------------------------------------------------------------------------
# Per-frame statistics
# ---------------------------------------------------------------------------
class FrameStats:
    """Collected statistics for a single processed frame."""

    __slots__ = (
        "frame_number",
        "timestamp_sec",
        "persons_detected",
        "inference_time_ms",
        "avg_confidence",
    )

    def __init__(
        self,
        frame_number: int,
        timestamp_sec: float,
        persons_detected: int,
        inference_time_ms: float,
        avg_confidence: float,
    ):
        self.frame_number = frame_number
        self.timestamp_sec = timestamp_sec
        self.persons_detected = persons_detected
        self.inference_time_ms = inference_time_ms
        self.avg_confidence = avg_confidence


# ---------------------------------------------------------------------------
# HUD overlay for live display
# ---------------------------------------------------------------------------
_HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
_HUD_SCALE = 0.55
_HUD_COLOR = (0, 255, 255)  # Cyan
_HUD_THICKNESS = 1


def _draw_hud(
    frame: np.ndarray,
    frame_num: int,
    persons: int,
    inference_ms: float,
    fps: float,
) -> np.ndarray:
    """Draw a heads-up display on the annotated frame."""
    lines = [
        f"Frame: {frame_num}",
        f"Persons: {persons}",
        f"Inference: {inference_ms:.1f}ms",
        f"FPS: {fps:.1f}",
    ]
    y = 25
    for line in lines:
        cv2.putText(frame, line, (10, y), _HUD_FONT, _HUD_SCALE, _HUD_COLOR, _HUD_THICKNESS)
        y += 22
    return frame


# ---------------------------------------------------------------------------
# VideoProcessor
# ---------------------------------------------------------------------------
class VideoProcessor:
    """
    Manages OpenCV video capture, frame processing loop,
    and annotated output generation.
    """

    # How often to log progress (every N frames)
    _LOG_INTERVAL = 50

    def __init__(
        self,
        source: str,
        config: PersonDetectionConfig,
        detector: PersonDetector,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the video processor.

        Parameters
        ----------
        source : str
            Path to a video file, or a string integer for webcam index.
        config : PersonDetectionConfig
            Pipeline configuration.
        detector : PersonDetector
            Initialized person detector.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.source = source
        self.config = config
        self.detector = detector
        self.logger = logger or setup_logger("video_processor")

        # Determine source type
        self.is_webcam = False
        self.webcam_index = -1
        try:
            self.webcam_index = int(source)
            self.is_webcam = True
        except (ValueError, TypeError):
            pass

        # Video capture and metadata (set during open)
        self.cap: Optional[cv2.VideoCapture] = None
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 0.0
        self.total_frames: int = 0
        self.duration_sec: float = 0.0

        # Collected frame statistics
        self.frame_stats: List[FrameStats] = []

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------
    def open(self) -> None:
        """
        Open the video source with OpenCV.

        Raises
        ------
        FileNotFoundError
            If the video file path does not exist.
        RuntimeError
            If OpenCV cannot open the source.
        """
        if self.is_webcam:
            self.logger.info(f"Opening webcam (index {self.webcam_index})...")
            self.cap = cv2.VideoCapture(self.webcam_index)

            if not self.cap.isOpened():
                raise RuntimeError(
                    f"Cannot open webcam at index {self.webcam_index}.\n"
                    f"Verify the webcam is connected and not in use by another application.\n"
                    f"Try a different index (e.g., 0, 1, 2)."
                )

            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = 0  # Unknown for webcam

            self.logger.info("Webcam opened successfully.")
            self.logger.info(f"Resolution: {self.width}x{self.height}")
            self.logger.info(f"FPS: {self.fps:.1f}")

        else:
            video_path = Path(self.source)
            if not video_path.exists():
                raise FileNotFoundError(
                    f"Video file not found: {video_path}\n"
                    f"Please verify the path and try again."
                )

            if not video_path.is_file():
                raise ValueError(f"Path is not a file: {video_path}")

            self.logger.info(f"Opening video: {video_path}")
            self.cap = cv2.VideoCapture(str(video_path))

            if not self.cap.isOpened():
                raise RuntimeError(
                    f"Cannot open video file: {video_path}\n"
                    f"The file may be corrupted or in an unsupported format.\n"
                    f"Supported formats: MP4, AVI, MOV, MKV."
                )

            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0.0

            self.logger.info("Video opened successfully.")
            self.logger.info(f"Resolution: {self.width}x{self.height}")
            self.logger.info(f"FPS: {self.fps:.1f}")
            self.logger.info(f"Total frames: {self.total_frames}")
            self.logger.info(f"Duration: {self.duration_sec:.1f}s")

    def close(self) -> None:
        """Release the video capture resource."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.logger.info("Video source released.")

    # ------------------------------------------------------------------
    # Video file processing
    # ------------------------------------------------------------------
    def process_video_file(self) -> Dict:
        """
        Process a video file: read → detect → annotate → write output.

        Returns
        -------
        Dict
            Session statistics for report generation.
        """
        self.open()

        # Setup output directories
        ensure_directory(self.config.videos_dir)
        if self.config.save_frames:
            ensure_directory(self.config.frames_dir)

        # Output video path
        source_name = Path(self.source).stem
        output_video_path = self.config.videos_dir / f"{source_name}_person_detection.mp4"

        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_video_path), fourcc, self.fps, (self.width, self.height)
        )
        if not writer.isOpened():
            self.close()
            raise RuntimeError(
                f"Failed to create output video writer.\n"
                f"Output path: {output_video_path}\n"
                f"Check directory permissions and available disk space."
            )

        self.logger.info(f"Output video: {output_video_path}")
        self.logger.info("Starting person detection...")

        self.frame_stats = []
        frame_number = 0
        total_detections = 0
        frames_with_persons = 0
        pipeline_start = time.perf_counter()

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break

                frame_number += 1
                timestamp_sec = frame_number / self.fps if self.fps > 0 else 0.0

                # Run detection
                detections, inference_ms = self.detector.detect(frame)
                num_persons = len(detections)
                total_detections += num_persons

                if num_persons > 0:
                    frames_with_persons += 1

                # Calculate average confidence for this frame
                avg_conf = (
                    sum(d.confidence for d in detections) / num_persons
                    if num_persons > 0
                    else 0.0
                )

                # Record stats
                self.frame_stats.append(
                    FrameStats(
                        frame_number=frame_number,
                        timestamp_sec=timestamp_sec,
                        persons_detected=num_persons,
                        inference_time_ms=inference_ms,
                        avg_confidence=avg_conf,
                    )
                )

                # Annotate and write
                annotated = self.detector.annotate(frame, detections)

                # Add HUD
                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0
                annotated = _draw_hud(
                    annotated, frame_number, num_persons, inference_ms, current_fps
                )

                writer.write(annotated)

                # Optionally save frame
                if self.config.save_frames and num_persons > 0:
                    frame_path = self.config.frames_dir / f"frame_{frame_number:06d}.jpg"
                    cv2.imwrite(str(frame_path), annotated)

                # Log progress periodically
                if frame_number % self._LOG_INTERVAL == 0 or frame_number == 1:
                    progress = ""
                    if self.total_frames > 0:
                        pct = (frame_number / self.total_frames) * 100
                        progress = f" ({pct:.1f}%)"
                    self.logger.info(
                        f"Processing frame {frame_number}{progress}... "
                        f"Persons detected: {num_persons} | "
                        f"Inference: {inference_ms:.1f}ms"
                    )

        except KeyboardInterrupt:
            self.logger.warning("Processing interrupted by user (Ctrl+C).")
        except MemoryError:
            self.logger.error(
                "Out of memory during video processing. "
                "Try reducing IMAGE_SIZE or processing a shorter video."
            )
            raise
        finally:
            writer.release()
            self.close()

        pipeline_elapsed = time.perf_counter() - pipeline_start

        self.logger.info("Processing completed.")
        self.logger.info(f"Saving output video: {output_video_path}")

        # Build session summary
        all_inference_times = [s.inference_time_ms for s in self.frame_stats]
        all_confidences = [
            s.avg_confidence for s in self.frame_stats if s.avg_confidence > 0
        ]

        session_stats = {
            "video_filename": Path(self.source).name,
            "video_path": str(Path(self.source).resolve()),
            "video_duration_sec": round(self.duration_sec, 2),
            "video_resolution": f"{self.width}x{self.height}",
            "video_fps": round(self.fps, 2),
            "total_frames_processed": frame_number,
            "total_frames_with_persons": frames_with_persons,
            "total_person_detections": total_detections,
            "average_inference_time_ms": round(
                sum(all_inference_times) / len(all_inference_times), 2
            )
            if all_inference_times
            else 0.0,
            "average_confidence": round(
                sum(all_confidences) / len(all_confidences), 4
            )
            if all_confidences
            else 0.0,
            "total_pipeline_time_sec": round(pipeline_elapsed, 2),
            "effective_fps": round(frame_number / pipeline_elapsed, 2)
            if pipeline_elapsed > 0
            else 0.0,
            "device": self.detector.device,
            "model": str(self.detector.model_path),
            "confidence_threshold": self.config.confidence_threshold,
            "image_size": self.config.image_size,
            "output_video": str(output_video_path),
            "save_frames": self.config.save_frames,
        }

        return session_stats

    # ------------------------------------------------------------------
    # Webcam processing
    # ------------------------------------------------------------------
    def process_webcam(self) -> None:
        """
        Process live webcam feed: read → detect → annotate → display.

        Press 'q' to quit.
        """
        self.open()

        self.logger.info("Starting live person detection from webcam...")
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

                # Run detection
                detections, inference_ms = self.detector.detect(frame)
                num_persons = len(detections)

                # Annotate
                annotated = self.detector.annotate(frame, detections)

                # HUD
                elapsed = time.perf_counter() - pipeline_start
                current_fps = frame_number / elapsed if elapsed > 0 else 0.0
                annotated = _draw_hud(
                    annotated, frame_number, num_persons, inference_ms, current_fps
                )

                # Display
                cv2.imshow("Person Detection — Press 'q' to quit", annotated)

                # Check for quit key
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    self.logger.info("Quit signal received.")
                    break

                # Log periodically
                if frame_number % self._LOG_INTERVAL == 0:
                    self.logger.info(
                        f"Frame {frame_number} | "
                        f"Persons: {num_persons} | "
                        f"Inference: {inference_ms:.1f}ms | "
                        f"FPS: {current_fps:.1f}"
                    )

        except KeyboardInterrupt:
            self.logger.info("Webcam stopped by user (Ctrl+C).")
        finally:
            cv2.destroyAllWindows()
            self.close()

        self.logger.info(f"Webcam session ended. Total frames processed: {frame_number}")
