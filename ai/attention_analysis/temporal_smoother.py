"""
Attention Analysis — Temporal Smoother
=========================================
Applies a sliding-window majority-vote filter to raw frame-by-frame
attention direction predictions to prevent jittery output.

A configurable window size controls the trade-off between stability
and responsiveness. Short, legitimate attention changes are preserved
when they appear consistently within the window.
"""

from collections import Counter, deque
from typing import Dict, Tuple

# pyrefly: ignore [missing-import]
from ai.attention_analysis.attention_classifier import AttentionDirection


class TemporalSmoother:
    """
    Smooths per-track attention direction predictions using a
    majority-vote sliding window.

    For each tracking ID, maintains a fixed-size deque of recent
    (direction, confidence) observations. The smoothed output is the
    most frequent direction within the window, with the average
    confidence of that direction's observations.
    """

    def __init__(self, window_size: int = 5):
        """
        Initialize the temporal smoother.

        Parameters
        ----------
        window_size : int
            Number of recent observations to consider for smoothing.
            Must be >= 1.
        """
        self.window_size = max(1, window_size)

        # track_id → deque of (AttentionDirection, confidence)
        self._history: Dict[int, deque] = {}

    def update(
        self,
        track_id: int,
        direction: AttentionDirection,
        confidence: float,
    ) -> Tuple[AttentionDirection, float]:
        """
        Add a new observation and return the smoothed direction.

        Parameters
        ----------
        track_id : int
            Tracking identifier for the shopper.
        direction : AttentionDirection
            Raw frame-level attention direction.
        confidence : float
            Raw frame-level confidence value.

        Returns
        -------
        Tuple[AttentionDirection, float]
            Smoothed direction and average confidence of that direction
            within the window. Returns (UNKNOWN, 0.0) if no clear majority.
        """
        if track_id not in self._history:
            self._history[track_id] = deque(maxlen=self.window_size)

        self._history[track_id].append((direction, confidence))

        return self._compute_smoothed(track_id)

    def _compute_smoothed(
        self, track_id: int
    ) -> Tuple[AttentionDirection, float]:
        """Compute majority-vote direction from the history window."""
        history = self._history.get(track_id)
        if not history:
            return AttentionDirection.UNKNOWN, 0.0

        # Count direction frequencies (exclude UNKNOWN from voting)
        direction_counts: Counter = Counter()
        direction_confidences: Dict[AttentionDirection, list] = {}

        for d, c in history:
            direction_counts[d] += 1
            if d not in direction_confidences:
                direction_confidences[d] = []
            direction_confidences[d].append(c)

        if not direction_counts:
            return AttentionDirection.UNKNOWN, 0.0

        # Find the most common direction
        most_common = direction_counts.most_common()
        top_direction = most_common[0][0]
        top_count = most_common[0][1]

        # If there is a tie at the top, check if any non-UNKNOWN direction
        # has a clear majority; otherwise return UNKNOWN
        if len(most_common) > 1 and most_common[1][1] == top_count:
            # Tie: prefer non-UNKNOWN directions
            non_unknown = [
                (d, c) for d, c in most_common
                if d != AttentionDirection.UNKNOWN
            ]
            if non_unknown:
                top_direction = non_unknown[0][0]
                top_count = non_unknown[0][1]

                # If multiple non-UNKNOWN directions tie, return UNKNOWN
                tied_non_unknown = [
                    d for d, c in non_unknown if c == top_count
                ]
                if len(tied_non_unknown) > 1:
                    return AttentionDirection.UNKNOWN, 0.0
            else:
                return AttentionDirection.UNKNOWN, 0.0

        # Calculate average confidence for the winning direction
        confs = direction_confidences.get(top_direction, [0.0])
        avg_confidence = sum(confs) / len(confs) if confs else 0.0

        return top_direction, round(avg_confidence, 4)

    def reset(self, track_id: int) -> None:
        """
        Clear the history for a specific track.

        Parameters
        ----------
        track_id : int
            Tracking identifier to clear.
        """
        self._history.pop(track_id, None)

    def reset_all(self) -> None:
        """Clear all tracking histories."""
        self._history.clear()

    def get_window_fill(self, track_id: int) -> int:
        """Return how many observations are in the window for a track."""
        history = self._history.get(track_id)
        return len(history) if history else 0
