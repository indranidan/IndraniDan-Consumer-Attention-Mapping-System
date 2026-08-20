"""
Module 4 — Gaze Estimator
===========================
Calculates 2D estimated viewing direction vector in camera frame coordinates
from 3D head orientation (yaw, pitch, roll).

Labels all directions as ESTIMATED ATTENTION / HEAD-POSE-BASED ATTENTION.
Never claims pixel-level pupil/eye gaze tracking.
"""

import math
from typing import Optional, Tuple

from app.module4.models import (
    AttentionDirection,
    AttentionState,
    GazeEstimate,
    HeadPoseData,
)


class Module4GazeEstimator:
    """
    Computes camera-space 2D estimated viewing ray from head pose angles.
    """

    def __init__(
        self,
        yaw_threshold: float = 15.0,
        pitch_threshold: float = 15.0,
        confidence_threshold: float = 0.50,
    ):
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold
        self.confidence_threshold = confidence_threshold

    def estimate_gaze(
        self,
        pose: HeadPoseData,
        fallback_origin: Optional[Tuple[int, int]] = None,
    ) -> Tuple[GazeEstimate, AttentionDirection, AttentionState]:
        """
        Derive 2D estimated gaze ray and discrete attention direction from head pose.

        Parameters
        ----------
        pose : HeadPoseData
            Estimated 3D head pose.
        fallback_origin : Tuple[int, int], optional
            Fallback (x, y) if nose landmark is unavailable.

        Returns
        -------
        Tuple[GazeEstimate, AttentionDirection, AttentionState]
            Estimated gaze vector, discrete direction, and attention state.
        """
        if not pose.face_detected or pose.confidence < self.confidence_threshold:
            return (
                GazeEstimate(
                    origin=fallback_origin or (0, 0),
                    direction=(0.0, 0.0),
                    confidence=pose.confidence,
                    method="head_pose_based_attention",
                    is_valid=False,
                ),
                AttentionDirection.UNKNOWN,
                AttentionState.UNKNOWN,
            )

        origin = pose.nose_point if pose.nose_point != (0, 0) else (fallback_origin or (0, 0))

        # Convert Euler angles to camera image space direction vector
        # Yaw: positive = right, Pitch: positive = up (in 3D, inverted for image Y)
        yaw_rad = math.radians(pose.yaw)
        pitch_rad = math.radians(-pose.pitch)

        dx = math.sin(yaw_rad)
        dy = math.sin(pitch_rad)

        mag = math.sqrt(dx * dx + dy * dy)
        if mag > 1e-4:
            norm_dx = dx / mag
            norm_dy = dy / mag
        else:
            norm_dx = 0.0
            norm_dy = 0.0

        # Classify discrete direction
        if abs(pose.yaw) > self.yaw_threshold:
            direction = AttentionDirection.RIGHT if pose.yaw > 0 else AttentionDirection.LEFT
        elif abs(pose.pitch) > self.pitch_threshold:
            direction = AttentionDirection.UP if pose.pitch > 0 else AttentionDirection.DOWN
        else:
            direction = AttentionDirection.CENTER

        gaze = GazeEstimate(
            origin=origin,
            direction=(round(norm_dx, 4), round(norm_dy, 4)),
            confidence=round(pose.confidence, 4),
            method="head_pose_based_attention",
            is_valid=True,
        )

        return gaze, direction, AttentionState.ATTENDING
