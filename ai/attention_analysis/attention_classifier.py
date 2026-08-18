"""
Attention Analysis — Attention Classifier
============================================
Converts head pose angles (yaw, pitch, roll) into discrete attention
directions and attention states.

All classifications are based on estimated head orientation, not
eye-level gaze tracking. Results are explicitly labeled accordingly.
"""

from enum import Enum
from typing import Tuple


class AttentionDirection(Enum):
    """Discrete attention direction derived from head pose."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class AttentionState(Enum):
    """Whether the shopper appears to be attending to a target."""

    ATTENDING = "ATTENDING"
    NOT_ATTENDING = "NOT_ATTENDING"
    UNKNOWN = "UNKNOWN"


class AttentionClassifier:
    """
    Classifies head pose angles into attention direction and state.

    Uses configurable yaw/pitch thresholds. Direction is UNKNOWN when
    confidence falls below the configured threshold — the system does
    not force a direction from unreliable estimates.
    """

    def __init__(
        self,
        yaw_threshold: float = 15.0,
        pitch_threshold: float = 15.0,
    ):
        """
        Initialize the attention classifier.

        Parameters
        ----------
        yaw_threshold : float
            Degrees of yaw beyond which the direction is LEFT or RIGHT.
            Within ±yaw_threshold is classified as CENTER (horizontally).
        pitch_threshold : float
            Degrees of pitch beyond which the direction is UP or DOWN.
            Within ±pitch_threshold is classified as CENTER (vertically).
        """
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold

    def classify(
        self,
        yaw: float,
        pitch: float,
        confidence: float,
        confidence_threshold: float,
    ) -> Tuple[AttentionDirection, AttentionState]:
        """
        Classify head pose into attention direction and state.

        Parameters
        ----------
        yaw : float
            Head yaw angle in degrees (positive = right, negative = left).
        pitch : float
            Head pitch angle in degrees (positive = up, negative = down).
        confidence : float
            Head pose estimation confidence (0.0 – 1.0).
        confidence_threshold : float
            Minimum confidence to produce a direction estimate.

        Returns
        -------
        Tuple[AttentionDirection, AttentionState]
            The classified direction and attention state.
            Returns (UNKNOWN, UNKNOWN) if confidence is below threshold.
        """
        # Low confidence → refuse to classify
        if confidence < confidence_threshold:
            return AttentionDirection.UNKNOWN, AttentionState.UNKNOWN

        # Yaw takes priority for combined poses (horizontal attention
        # is more relevant in retail shelf-viewing scenarios)
        if abs(yaw) > self.yaw_threshold:
            if yaw > 0:
                direction = AttentionDirection.RIGHT
            else:
                direction = AttentionDirection.LEFT
        elif abs(pitch) > self.pitch_threshold:
            if pitch > 0:
                direction = AttentionDirection.UP
            else:
                direction = AttentionDirection.DOWN
        else:
            direction = AttentionDirection.CENTER

        # Determine state: any valid direction means the system can
        # estimate where the person is looking
        state = AttentionState.ATTENDING

        return direction, state
