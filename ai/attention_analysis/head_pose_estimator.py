"""
Attention Analysis — Head Pose Estimator
==========================================
Estimates head orientation (yaw, pitch, roll) from a person crop using
MediaPipe FaceLandmarker (Tasks API) and OpenCV solvePnP.

This module provides *estimated head-orientation-based attention direction*.
It does NOT claim pixel-level eye gaze tracking. Typical retail CCTV cameras
do not provide sufficient eye resolution for true gaze estimation.

The primary attention signal is head pose (yaw/pitch/roll), which serves as
a reliable proxy for approximate gaze direction at the resolution available
from overhead or angled retail cameras.
"""

import logging
import os
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.logger import setup_logger


# ---------------------------------------------------------------------------
# Head Pose Result
# ---------------------------------------------------------------------------
class HeadPoseResult(NamedTuple):
    """Result of a head pose estimation attempt."""

    yaw: float              # Left/right head orientation (degrees)
    pitch: float            # Up/down head orientation (degrees)
    roll: float             # Head tilt (degrees)
    face_detected: bool     # Whether a face was successfully detected
    confidence: float       # Estimation confidence (0.0 – 1.0)
    face_bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) of detected face region
    nose_point: Tuple[int, int]           # 2D nose tip in frame coordinates
    detection_method: str   # Always "head_orientation" — never claims eye gaze


# Sentinel for failed detection
NO_DETECTION = HeadPoseResult(
    yaw=0.0, pitch=0.0, roll=0.0,
    face_detected=False, confidence=0.0,
    face_bbox=(0, 0, 0, 0), nose_point=(0, 0),
    detection_method="head_orientation",
)


# ---------------------------------------------------------------------------
# 3D face model points for solvePnP
# ---------------------------------------------------------------------------
_MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),         # Nose tip
    (0.0, 330.0, -65.0),     # Chin (positive Y points DOWN, matching OpenCV image space)
    (-225.0, -170.0, -135.0),# Left eye left corner (person's right eye, viewer's left)
    (225.0, -170.0, -135.0), # Right eye right corner (person's left eye, viewer's right)
    (-150.0, 150.0, -125.0), # Left mouth corner
    (150.0, 150.0, -125.0),  # Right mouth corner
], dtype=np.float64)

# MediaPipe FaceLandmarker landmark indices for the 6 key points
_LANDMARK_INDICES = [
    1,    # Nose tip
    199,  # Chin
    33,   # Left eye left corner
    263,  # Right eye right corner
    61,   # Left mouth corner
    291,  # Right mouth corner
]

# Minimum face size (pixels) to attempt head pose estimation
_MIN_FACE_SIZE = 15

# Default model path
_DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"


class HeadPoseEstimator:
    """
    Estimates head orientation from a person bounding box crop using
    MediaPipe FaceLandmarker for landmark detection and OpenCV solvePnP
    for 3D pose recovery.

    All outputs are clearly labeled as estimated head orientation,
    not eye-level gaze tracking.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        model_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the head pose estimator.

        Parameters
        ----------
        min_detection_confidence : float
            Minimum confidence for face detection (0.0 – 1.0).
        model_path : Path, optional
            Path to the face_landmarker.task model file.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.logger = logger or setup_logger("head_pose_estimator")

        try:
            # pyrefly: ignore [missing-import]
            import mediapipe as mp
            # pyrefly: ignore [missing-import]
            from mediapipe.tasks import python as mp_python
            # pyrefly: ignore [missing-import]
            from mediapipe.tasks.python import vision as mp_vision
        except ImportError:
            raise ImportError(
                "mediapipe is required for head pose estimation.\n"
                "Install it with: pip install 'mediapipe>=0.10.0,<1.0.0'"
            )

        # Resolve model path
        resolved_path = model_path or _DEFAULT_MODEL_PATH
        if not resolved_path.exists():
            raise FileNotFoundError(
                f"FaceLandmarker model not found at: {resolved_path}\n"
                f"Download it from: https://storage.googleapis.com/mediapipe-models/"
                f"face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            )

        self.logger.info(f"Loading FaceLandmarker model: {resolved_path}")

        # Store mediapipe references
        self._mp = mp
        self._mp_vision = mp_vision

        # Create FaceLandmarker with IMAGE mode
        base_options = mp_python.BaseOptions(
            model_asset_path=str(resolved_path)
        )
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_detection_confidence,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        self.logger.info(
            f"Head pose estimator initialized "
            f"(MediaPipe FaceLandmarker Tasks API, min_det_conf={min_detection_confidence})"
        )

    def estimate(
        self,
        frame: np.ndarray,
        person_bbox: Tuple[int, int, int, int],
    ) -> HeadPoseResult:
        """
        Estimate head pose for a detected person.

        Parameters
        ----------
        frame : np.ndarray
            Full BGR video frame.
        person_bbox : tuple
            Person bounding box (x1, y1, x2, y2) in frame coordinates.

        Returns
        -------
        HeadPoseResult
            Estimated head orientation with confidence, or NO_DETECTION.
        """
        x1, y1, x2, y2 = person_bbox
        person_w = x2 - x1
        person_h = y2 - y1

        if person_w < _MIN_FACE_SIZE or person_h < _MIN_FACE_SIZE:
            return NO_DETECTION

        # Try upper 35% crop first, with upper 50% crop fallback if needed
        crops_to_try = [0.35, 0.50]
        result = None
        used_head_y1, used_head_x1 = 0, 0
        used_crop_w, used_crop_h = 0, 0

        for height_ratio in crops_to_try:
            head_h = int(person_h * height_ratio)
            head_y1 = max(0, y1)
            head_y2 = min(frame.shape[0], y1 + head_h)
            head_x1 = max(0, x1)
            head_x2 = min(frame.shape[1], x2)

            if head_y2 <= head_y1 or head_x2 <= head_x1:
                continue

            head_crop = frame[head_y1:head_y2, head_x1:head_x2]
            crop_h, crop_w = head_crop.shape[:2]

            if crop_h < _MIN_FACE_SIZE or crop_w < _MIN_FACE_SIZE:
                continue

            rgb_crop = cv2.cvtColor(head_crop, cv2.COLOR_BGR2RGB)
            mp_image = self._mp.Image(
                image_format=self._mp.ImageFormat.SRGB,
                data=rgb_crop,
            )

            try:
                res = self.landmarker.detect(mp_image)
                if res and res.face_landmarks and len(res.face_landmarks) > 0:
                    result = res
                    used_head_y1 = head_y1
                    used_head_x1 = head_x1
                    used_crop_w = crop_w
                    used_crop_h = crop_h
                    break
            except Exception:
                continue

        if not result or not result.face_landmarks:
            return NO_DETECTION

        face_landmarks = result.face_landmarks[0]

        # Extract the 6 key 2D landmark coordinates in crop space
        image_points = []
        visibility_sum = 0.0

        for idx in _LANDMARK_INDICES:
            if idx >= len(face_landmarks):
                return NO_DETECTION

            lm = face_landmarks[idx]
            px = lm.x * used_crop_w
            py = lm.y * used_crop_h
            image_points.append((px, py))

            vis = getattr(lm, "visibility", 0.8)
            visibility_sum += vis if vis is not None else 0.8

        image_points_np = np.array(image_points, dtype=np.float64)

        # Approximate camera intrinsics
        focal_length = used_crop_w
        camera_matrix = np.array([
            [focal_length, 0, used_crop_w / 2.0],
            [0, focal_length, used_crop_h / 2.0],
            [0, 0, 1.0],
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # Solve PnP
        try:
            success, rvec, tvec = cv2.solvePnP(
                _MODEL_POINTS_3D,
                image_points_np,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
        except Exception:
            return NO_DETECTION

        if not success:
            return NO_DETECTION

        # Convert rotation vector → Euler angles using RQDecomp3x3
        rmat, _ = cv2.Rodrigues(rvec)

        try:
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            pitch = float(angles[0])
            yaw = float(angles[1])
            roll = float(angles[2])
        except Exception:
            return NO_DETECTION

        # Clamp extreme values
        yaw = max(-90.0, min(90.0, yaw))
        pitch = max(-90.0, min(90.0, pitch))
        roll = max(-90.0, min(90.0, roll))

        # Compute confidence based on visibility and face landmark span quality
        avg_visibility = visibility_sum / len(_LANDMARK_INDICES)
        lm_xs = [p[0] for p in image_points]
        lm_ys = [p[1] for p in image_points]
        face_w = max(lm_xs) - min(lm_xs)
        face_h = max(lm_ys) - min(lm_ys)

        face_size_quality = min(1.0, (face_w * face_h) / 225.0)
        confidence = float(np.clip(avg_visibility * 0.5 + face_size_quality * 0.5, 0.0, 1.0))

        # Nose tip in original frame coordinates
        nose_lm = face_landmarks[1]
        nose_x = int(nose_lm.x * used_crop_w) + used_head_x1
        nose_y = int(nose_lm.y * used_crop_h) + used_head_y1

        # Face bbox in original frame coordinates
        face_x1 = int(min(lm_xs)) + used_head_x1
        face_y1 = int(min(lm_ys)) + used_head_y1
        face_x2 = int(max(lm_xs)) + used_head_x1
        face_y2 = int(max(lm_ys)) + used_head_y1

        return HeadPoseResult(
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            face_detected=True,
            confidence=round(confidence, 4),
            face_bbox=(face_x1, face_y1, face_x2, face_y2),
            nose_point=(nose_x, nose_y),
            detection_method="head_orientation",
        )

    def close(self) -> None:
        """Release MediaPipe resources."""
        if hasattr(self, "landmarker") and self.landmarker:
            self.landmarker.close()
