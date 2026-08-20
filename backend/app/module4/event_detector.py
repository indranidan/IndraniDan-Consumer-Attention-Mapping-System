"""
Module 4 — Attention Event Detector
====================================
Groups consecutive attention frames into discrete, structured attention events.
Correctly handles repeated attention events when a shopper looks away and looks back.
"""

from typing import Dict, List, Optional
import uuid

from app.module4.models import (
    AttentionDirection,
    AttentionEventRecord,
    AttentionState,
    AttentionType,
    GazeEstimate,
)


class _TrackActiveEvent:
    """Internal active attention state for a single track ID."""

    def __init__(self, track_id: int):
        self.track_id = track_id
        self.active_event: Optional[AttentionEventRecord] = None
        self.completed_events: List[AttentionEventRecord] = []
        self.target_visit_counts: Dict[str, int] = {}
        self.confidence_sum: float = 0.0
        self.confidence_count: int = 0


class Module4AttentionEventDetector:
    """
    Manages attention event lifecycles per tracked person.
    """

    def __init__(self, min_duration_sec: float = 0.3):
        self.min_duration_sec = min_duration_sec
        self._states: Dict[int, _TrackActiveEvent] = {}

    def _get_state(self, track_id: int) -> _TrackActiveEvent:
        if track_id not in self._states:
            self._states[track_id] = _TrackActiveEvent(track_id)
        return self._states[track_id]

    def _close_active(
        self,
        st: _TrackActiveEvent,
        frame: int,
        timestamp: float,
        status: str = "completed",
    ) -> Optional[AttentionEventRecord]:
        if st.active_event is None:
            return None

        ev = st.active_event
        ev.close(timestamp, frame, status=status)

        if ev.duration_seconds is not None and ev.duration_seconds >= self.min_duration_sec:
            st.completed_events.append(ev)
            result = ev
        else:
            result = None

        st.active_event = None
        st.confidence_sum = 0.0
        st.confidence_count = 0
        return result

    def update_track_attention(
        self,
        track_id: int,
        frame_number: int,
        timestamp: float,
        target_id: Optional[str],
        target_name: Optional[str],
        target_type: Optional[str],
        direction: AttentionDirection,
        confidence: float,
        zone_id: str,
        state: AttentionState,
        session_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        store_id: Optional[str] = None,
        gaze: Optional[GazeEstimate] = None,
    ) -> None:
        """
        Feed a frame-level observation for a track ID.
        """
        st = self._get_state(track_id)

        # If shopper is not attending, or direction is unknown, or confidence low -> close active event
        if state != AttentionState.ATTENDING or direction == AttentionDirection.UNKNOWN:
            if st.active_event is not None:
                self._close_active(st, frame_number, timestamp, status="completed")
            return

        eff_target_id = target_id or "unknown"
        eff_target_name = target_name or "Unknown"
        eff_target_type = target_type or "unknown"

        # Determine attention type
        if eff_target_type == "shelf":
            attn_type = AttentionType.SHELF_ATTENTION.value
        elif eff_target_type == "product":
            attn_type = AttentionType.PRODUCT_ATTENTION.value
        else:
            attn_type = AttentionType.HEAD_POSE_ATTENTION.value

        # Check if already attending to the same target -> extend event
        if st.active_event is not None:
            if st.active_event.target_id == eff_target_id:
                st.confidence_sum += confidence
                st.confidence_count += 1
                st.active_event.confidence = round(st.confidence_sum / max(1, st.confidence_count), 4)
                st.active_event.attention_direction = direction.value
                return
            else:
                # Target changed -> close old event, start new event
                self._close_active(st, frame_number, timestamp, status="completed")

        # Start a new attention event
        st.target_visit_counts[eff_target_id] = st.target_visit_counts.get(eff_target_id, 0) + 1
        visit_no = st.target_visit_counts[eff_target_id]

        ev = AttentionEventRecord(
            event_id=str(uuid.uuid4()),
            track_id=track_id,
            session_id=session_id,
            camera_id=camera_id,
            store_id=store_id,
            timestamp=timestamp,
            start_time=timestamp,
            attention_type=attn_type,
            target_type=eff_target_type,
            target_id=eff_target_id,
            target_name=eff_target_name,
            zone_id=zone_id,
            attention_direction=direction.value,
            confidence=confidence,
            status="active",
            visit_number=visit_no,
            start_frame=frame_number,
            gaze_origin=gaze.origin if gaze else None,
            gaze_direction=gaze.direction if gaze else None,
        )
        st.active_event = ev
        st.confidence_sum = confidence
        st.confidence_count = 1

    def handle_lost_track(
        self,
        track_id: int,
        frame_number: int,
        timestamp: float,
    ) -> List[AttentionEventRecord]:
        """Close active event for a lost track."""
        if track_id not in self._states:
            return []
        st = self._states[track_id]
        closed = self._close_active(st, frame_number, timestamp, status="track_lost")
        return [closed] if closed else []

    def close_all(self, frame_number: int, timestamp: float) -> None:
        """Close all remaining active events (e.g. at stream end)."""
        for st in self._states.values():
            if st.active_event is not None:
                self._close_active(st, frame_number, timestamp, status="completed")

    def get_all_completed_events(self) -> List[AttentionEventRecord]:
        """Return all completed attention events."""
        events: List[AttentionEventRecord] = []
        for st in self._states.values():
            events.extend(st.completed_events)
        return sorted(events, key=lambda e: e.start_time)

    def get_events_for_track(self, track_id: int) -> List[AttentionEventRecord]:
        if track_id not in self._states:
            return []
        return list(self._states[track_id].completed_events)
