"""
Attention Analysis — Attention Tracker
=========================================
Manages attention events per shopper. Tracks when a shopper's estimated
attention direction is consistently directed toward a configured target
and records structured attention events with duration.

Distinguishes between:
- Zone dwell time: time physically observed inside a zone
- Estimated attention time: time the estimated head/gaze direction is
  consistently directed toward a configured target

Preserves separate events for repeated attention (no auto-merge).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ai.attention_analysis.attention_classifier import AttentionDirection, AttentionState
from ai.logger import setup_logger


@dataclass
class AttentionEvent:
    """A single attention event — a period where a shopper's estimated
    attention was directed toward a specific target."""

    tracking_id: int
    zone_id: str
    target_type: str        # "shelf", "zone", "product", "unknown"
    target_id: str
    target_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    attention_direction: str = "UNKNOWN"
    confidence: float = 0.0
    status: str = "active"  # "active", "completed", "track_lost"
    visit_number: int = 1
    start_frame: int = 0
    end_frame: Optional[int] = None
    gaze_origin: Optional[Tuple[int, int]] = None
    gaze_direction: Optional[Tuple[float, float]] = None

    def close(self, end_time: float, end_frame: int, status: str = "completed") -> None:
        """Close this attention event."""
        self.end_time = end_time
        self.end_frame = end_frame
        self.duration_seconds = round(end_time - self.start_time, 3)
        self.status = status

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "tracking_id": self.tracking_id,
            "zone_id": self.zone_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3) if self.end_time is not None else None,
            "duration_seconds": self.duration_seconds,
            "attention_direction": self.attention_direction,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "visit_number": self.visit_number,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "gaze_origin": list(self.gaze_origin) if self.gaze_origin else None,
            "gaze_direction": list(self.gaze_direction) if self.gaze_direction else None,
        }


@dataclass
class _TrackAttentionState:
    """Internal per-track attention state."""

    active_event: Optional[AttentionEvent] = None
    completed_events: List[AttentionEvent] = field(default_factory=list)
    # target_id → visit count (for numbering repeated visits)
    visit_counts: Dict[str, int] = field(default_factory=dict)
    # Running confidence accumulator for active event
    confidence_sum: float = 0.0
    confidence_count: int = 0
    # Unknown/low-confidence frame count
    unknown_count: int = 0
    total_observations: int = 0


class AttentionTracker:
    """
    Tracks attention events per shopper.

    For each tracked shopper, monitors whether their estimated attention
    is directed toward a configured target and generates structured
    attention events when attention is sustained.

    Repeated attention to the same target creates separate events
    (no automatic merging).
    """

    def __init__(
        self,
        min_duration: float = 0.3,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the attention tracker.

        Parameters
        ----------
        min_duration : float
            Minimum duration in seconds required to record an attention event.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.min_duration = min_duration
        self.logger = logger or setup_logger("attention_tracker")
        self._states: Dict[int, _TrackAttentionState] = {}

    def _get_state(self, track_id: int) -> _TrackAttentionState:
        """Get or create per-track attention state."""
        if track_id not in self._states:
            self._states[track_id] = _TrackAttentionState()
        return self._states[track_id]

    def _close_active_event(
        self, ts: _TrackAttentionState, frame: int, timestamp: float, status: str = "completed"
    ) -> Optional[AttentionEvent]:
        """Close active event and keep it only if duration meets min_duration."""
        if ts.active_event is None:
            return None
        ev = ts.active_event
        ev.close(timestamp, frame, status=status)
        if ev.duration_seconds is not None and ev.duration_seconds >= self.min_duration:
            ts.completed_events.append(ev)
            res = ev
        else:
            res = None
        ts.active_event = None
        ts.confidence_sum = 0.0
        ts.confidence_count = 0
        return res

    def update(
        self,
        track_id: int,
        frame: int,
        timestamp: float,
        target_id: Optional[str],
        target_name: Optional[str],
        target_type: Optional[str],
        direction: AttentionDirection,
        confidence: float,
        zone_id: str,
        state: AttentionState,
        gaze_origin: Optional[Tuple[int, int]] = None,
        gaze_direction: Optional[Tuple[float, float]] = None,
    ) -> None:
        """
        Update attention tracking for a shopper.
        """
        ts = self._get_state(track_id)
        ts.total_observations += 1

        # Handle unknown/low-confidence state
        if state == AttentionState.UNKNOWN or direction == AttentionDirection.UNKNOWN:
            ts.unknown_count += 1
            # Close active event if any
            if ts.active_event is not None:
                self._close_active_event(ts, frame, timestamp, status="completed")
            return

        effective_target_id = target_id or "unknown"
        effective_target_name = target_name or "Unknown"
        effective_target_type = target_type or "unknown"

        # Check if this is the same target as the active event
        if ts.active_event is not None:
            if ts.active_event.target_id == effective_target_id:
                # Same target → extend the active event
                ts.confidence_sum += confidence
                ts.confidence_count += 1
                ts.active_event.confidence = round(
                    ts.confidence_sum / ts.confidence_count, 4
                )
                ts.active_event.attention_direction = direction.value
                # Update spatial data with latest observation
                if gaze_origin:
                    ts.active_event.gaze_origin = gaze_origin
                if gaze_direction:
                    ts.active_event.gaze_direction = gaze_direction
                return
            else:
                # Different target → close current, start new
                self._close_active_event(ts, frame, timestamp, status="completed")

        # Start a new attention event
        visit_key = effective_target_id
        ts.visit_counts[visit_key] = ts.visit_counts.get(visit_key, 0) + 1

        ts.active_event = AttentionEvent(
            tracking_id=track_id,
            zone_id=zone_id,
            target_type=effective_target_type,
            target_id=effective_target_id,
            target_name=effective_target_name,
            start_time=timestamp,
            attention_direction=direction.value,
            confidence=confidence,
            visit_number=ts.visit_counts[visit_key],
            start_frame=frame,
            gaze_origin=gaze_origin,
            gaze_direction=gaze_direction,
        )
        ts.confidence_sum = confidence
        ts.confidence_count = 1

    def handle_lost_track(
        self, track_id: int, frame: int, timestamp: float
    ) -> List[AttentionEvent]:
        """
        Handle a lost track by closing any active attention event.
        """
        ts = self._states.get(track_id)
        if ts is None or ts.active_event is None:
            return []

        closed_ev = self._close_active_event(ts, frame, timestamp, status="track_lost")
        return [closed_ev] if closed_ev else []

    def close_remaining_events(self, frame: int, timestamp: float) -> None:
        """Close all remaining active attention events (e.g., at video end)."""
        for track_id, ts in self._states.items():
            if ts.active_event is not None:
                self._close_active_event(ts, frame, timestamp, status="completed")

    def get_all_events(self) -> List[AttentionEvent]:
        """Return all completed attention events across all tracks."""
        events = []
        for ts in self._states.values():
            events.extend(ts.completed_events)
        return events

    def get_events_for_track(self, track_id: int) -> List[AttentionEvent]:
        """Return all completed attention events for a specific track."""
        ts = self._states.get(track_id)
        if ts is None:
            return []
        return list(ts.completed_events)

    def get_events_for_target(self, target_id: str) -> List[AttentionEvent]:
        """Return all completed attention events for a specific target."""
        events = []
        for ts in self._states.values():
            for ev in ts.completed_events:
                if ev.target_id == target_id:
                    events.append(ev)
        return events

    def get_active_event(self, track_id: int) -> Optional[AttentionEvent]:
        """Return the active attention event for a track, if any."""
        ts = self._states.get(track_id)
        if ts is None:
            return None
        return ts.active_event

    def get_track_stats(self, track_id: int) -> dict:
        """Return attention statistics for a specific track."""
        ts = self._states.get(track_id)
        if ts is None:
            return {
                "total_observations": 0,
                "unknown_count": 0,
                "event_count": 0,
            }

        return {
            "total_observations": ts.total_observations,
            "unknown_count": ts.unknown_count,
            "event_count": len(ts.completed_events),
        }

    @property
    def total_events(self) -> int:
        """Total number of completed attention events."""
        return sum(len(ts.completed_events) for ts in self._states.values())

    @property
    def total_active_events(self) -> int:
        """Number of currently active attention events."""
        return sum(
            1 for ts in self._states.values() if ts.active_event is not None
        )

    @property
    def all_track_ids(self) -> List[int]:
        """Return all tracked shopper IDs."""
        return list(self._states.keys())
