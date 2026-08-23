"""
Module 4 — Head Pose Estimator
=================================
Estimates 3D head orientation (yaw, pitch, roll) from person bounding boxes.
Associates each head pose with the corresponding ByteTrack ID.

Explicitly labeled as estimated head-orientation-based proxy,
not pixel-level eye gaze tracking.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from app.modules.attention.models import HeadPoseData

_MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, 330.0, -65.0),      # Chin (Y positive downwards)
    (-225.0, -170.0, -135.0), # Left eye left corner
    (225.0, -170.0, -135.0),  # Right eye right corner
    (-150.0, 150.0, -125.0),  # Left mouth corner
    (150.0, 150.0, -125.0),   # Right mouth corner
], dtype=np.float64)

_LANDMARK_INDICES = [1, 199, 33, 263, 61, 291]
_MIN_FACE_SIZE = 15

# Default FaceLandmarker model path
_DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "ai"
    / "models"
    / "face_landmarker.task"
)


class Module4HeadPoseEstimator:
    """
    Recovers 3D head orientation (yaw, pitch, roll) using MediaPipe FaceLandmarker
    and OpenCV solvePnP.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        model_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger("module4_head_pose")
        self.min_detection_confidence = min_detection_confidence
        self._landmarker = None

        resolved_path = model_path or _DEFAULT_MODEL_PATH
        if resolved_path.exists():
            self._init_landmarker(resolved_path)
        else:
            self.logger.warning(
                f"FaceLandmarker model not found at {resolved_path}. "
                f"Head pose estimation will run in fallback/simulation mode if needed."
            )

    def _init_landmarker(self, model_path: Path) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            self._mp = mp
            base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
            options = mp_vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=self.min_detection_confidence,
                min_face_presence_confidence=self.min_detection_confidence,
                min_tracking_confidence=0.5,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
            self.logger.info("MediaPipe FaceLandmarker successfully initialized.")
        except Exception as exc:
            self.logger.warning(f"Could not initialize MediaPipe FaceLandmarker: {exc}")
            self._landmarker = None

    def estimate_from_crop(
        self,
        frame: np.ndarray,
        person_bbox: Tuple[int, int, int, int],
    ) -> HeadPoseData:
        """
        Estimate head orientation from person bounding box in frame.

        Parameters
        ----------
        frame : np.ndarray
            BGR image frame.
        person_bbox : Tuple[int, int, int, int]
            (x1, y1, x2, y2)

        Returns
        -------
        HeadPoseData
            Detailed head pose or unavailable status.
        """
        x1, y1, x2, y2 = person_bbox
        person_w = x2 - x1
        person_h = y2 - y1

        if person_w < _MIN_FACE_SIZE or person_h < _MIN_FACE_SIZE:
            return HeadPoseData(status="unavailable")

        if self._landmarker is None:
            # When landmarker is unavailable (e.g. headless without model file), return unavailable
            return HeadPoseData(status="unavailable")

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
                res = self._landmarker.detect(mp_image)
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
            return HeadPoseData(status="unavailable")

        face_landmarks = result.face_landmarks[0]
        image_points = []
        visibility_sum = 0.0

        for idx in _LANDMARK_INDICES:
            if idx >= len(face_landmarks):
                return HeadPoseData(status="unavailable")
            lm = face_landmarks[idx]
            px = lm.x * used_crop_w
            py = lm.y * used_crop_h
            image_points.append((px, py))
            vis = getattr(lm, "visibility", 0.8)
            visibility_sum += vis if vis is not None else 0.8

        image_points_np = np.array(image_points, dtype=np.float64)

        focal_length = used_crop_w
        camera_matrix = np.array([
            [focal_length, 0, used_crop_w / 2.0],
            [0, focal_length, used_crop_h / 2.0],
            [0, 0, 1.0],
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        try:
            success, rvec, tvec = cv2.solvePnP(
                _MODEL_POINTS_3D,
                image_points_np,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
        except Exception:
            return HeadPoseData(status="unavailable")

        if not success:
            return HeadPoseData(status="unavailable")

        rmat, _ = cv2.Rodrigues(rvec)
        try:
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            pitch = float(angles[0])
            yaw = float(angles[1])
            roll = float(angles[2])
        except Exception:
            return HeadPoseData(status="unavailable")

        yaw = max(-90.0, min(90.0, yaw))
        pitch = max(-90.0, min(90.0, pitch))
        roll = max(-90.0, min(90.0, roll))

        avg_visibility = visibility_sum / len(_LANDMARK_INDICES)
        lm_xs = [p[0] for p in image_points]
        lm_ys = [p[1] for p in image_points]
        face_w = max(lm_xs) - min(lm_xs)
        face_h = max(lm_ys) - min(lm_ys)

        face_size_quality = min(1.0, (face_w * face_h) / 225.0)
        confidence = float(np.clip(avg_visibility * 0.5 + face_size_quality * 0.5, 0.0, 1.0))

        nose_lm = face_landmarks[1]
        nose_x = int(nose_lm.x * used_crop_w) + used_head_x1
        nose_y = int(nose_lm.y * used_crop_h) + used_head_y1

        face_x1 = int(min(lm_xs)) + used_head_x1
        face_y1 = int(min(lm_ys)) + used_head_y1
        face_x2 = int(max(lm_xs)) + used_head_x1
        face_y2 = int(max(lm_ys)) + used_head_y1

        status_str = "available" if confidence >= self.min_detection_confidence else "low_confidence"

        return HeadPoseData(
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            face_detected=True,
            confidence=round(confidence, 4),
            face_bbox=(face_x1, face_y1, face_x2, face_y2),
            nose_point=(nose_x, nose_y),
            status=status_str,
            method="head_orientation",
        )

    def close(self) -> None:
        """Release landmarker resources."""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
