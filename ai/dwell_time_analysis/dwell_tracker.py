"""
Dwell-Time Analysis — Dwell Tracker
=======================================
Core dwell-time tracking engine. Measures how long tracked shoppers
remain inside each configured zone using center-point position and
video timestamps.

Key features:
- Per-shopper, per-zone dwell event tracking
- Repeated zone visit preservation (separate visit records)
- Configurable gap tolerance for brief tracking interruptions
- Overlapping zone support (shopper can be in multiple zones)
- Track-lost vs. confirmed exit distinction
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ai.logger import setup_logger


@dataclass
class DwellEvent:
    """Record of a single shopper visit to a specific zone."""

    tracking_id: int
    zone_id: str
    zone_name: str
    visit_number: int

    entry_frame: int
    entry_time: float

    exit_frame: Optional[int] = None
    exit_time: Optional[float] = None

    frames_observed: int = 0
    total_confidence: float = 0.0
    confidence_samples: int = 0

    status: str = "active"  # "active", "completed", "track_lost"

    @property
    def dwell_seconds(self) -> Optional[float]:
        """Calculate dwell duration in seconds."""
        if self.exit_time is not None and self.entry_time is not None:
            return self.exit_time - self.entry_time
        return None

    @property
    def average_confidence(self) -> float:
        """Average detection confidence during this visit."""
        if self.confidence_samples > 0:
            return self.total_confidence / self.confidence_samples
        return 0.0

    def update_presence(self, frame: int, confidence: float) -> None:
        """Update the visit with a new frame observation."""
        self.frames_observed += 1
        self.total_confidence += confidence
        self.confidence_samples += 1

    def close(self, frame: int, timestamp: float, status: str = "completed") -> None:
        """Close the dwell event with an exit frame and status."""
        self.exit_frame = frame
        self.exit_time = timestamp
        self.status = status

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        result = {
            "tracking_id": self.tracking_id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "visit_number": self.visit_number,
            "entry_frame": self.entry_frame,
            "entry_time": round(self.entry_time, 3),
            "exit_frame": self.exit_frame,
            "exit_time": round(self.exit_time, 3) if self.exit_time is not None else None,
            "dwell_seconds": round(self.dwell_seconds, 3) if self.dwell_seconds is not None else None,
            "frames_observed": self.frames_observed,
            "average_confidence": round(self.average_confidence, 4),
            "status": self.status,
        }
        return result


class ShopperDwellState:
    """Manages dwell state for a single tracked shopper."""

    def __init__(self, track_id: int):
        self.track_id = track_id

        # Currently active zone visits (zone_id -> DwellEvent)
        self.active_visits: Dict[str, DwellEvent] = {}

        # All completed/closed dwell events
        self.completed_visits: List[DwellEvent] = []

        # Per-zone visit counter for visit_number assignment
        self.visit_counts: Dict[str, int] = {}

        # Track the last frame this shopper was seen (for gap tolerance)
        self.last_seen_frame: int = 0

        # Track which zones had active visits but the shopper left temporarily
        # Maps zone_id -> frame when shopper was last seen in that zone
        self._zone_last_seen: Dict[str, int] = {}

    def enter_zone(
        self, zone_id: str, zone_name: str, frame: int, timestamp: float
    ) -> DwellEvent:
        """Start a new dwell event for a zone entry."""
        # Increment visit counter
        self.visit_counts[zone_id] = self.visit_counts.get(zone_id, 0) + 1
        visit_number = self.visit_counts[zone_id]

        event = DwellEvent(
            tracking_id=self.track_id,
            zone_id=zone_id,
            zone_name=zone_name,
            visit_number=visit_number,
            entry_frame=frame,
            entry_time=timestamp,
        )
        self.active_visits[zone_id] = event
        self._zone_last_seen[zone_id] = frame
        return event

    def exit_zone(self, zone_id: str, frame: int, timestamp: float) -> Optional[DwellEvent]:
        """Close an active dwell event for a zone exit."""
        if zone_id not in self.active_visits:
            return None

        event = self.active_visits.pop(zone_id)
        event.close(frame, timestamp, status="completed")
        self.completed_visits.append(event)
        self._zone_last_seen.pop(zone_id, None)
        return event

    def update_presence(
        self, zone_id: str, frame: int, confidence: float
    ) -> None:
        """Update an active visit with a new frame observation."""
        if zone_id in self.active_visits:
            self.active_visits[zone_id].update_presence(frame, confidence)
            self._zone_last_seen[zone_id] = frame

    def should_close_zone_visit(
        self, zone_id: str, current_frame: int, gap_tolerance: int
    ) -> bool:
        """Check if a zone visit should be closed due to gap exceeding tolerance."""
        last_seen = self._zone_last_seen.get(zone_id)
        if last_seen is None:
            return False
        return (current_frame - last_seen) > gap_tolerance

    def close_all_active(self, frame: int, timestamp: float, status: str = "completed") -> List[DwellEvent]:
        """Close all active visits with the given status."""
        closed = []
        for zone_id in list(self.active_visits.keys()):
            event = self.active_visits.pop(zone_id)
            event.close(frame, timestamp, status=status)
            self.completed_visits.append(event)
            closed.append(event)
        self._zone_last_seen.clear()
        return closed

    def get_all_events(self) -> List[DwellEvent]:
        """Return all events (completed + active)."""
        return self.completed_visits + list(self.active_visits.values())

    def get_active_zone_ids(self) -> Set[str]:
        """Return set of zone IDs with active visits."""
        return set(self.active_visits.keys())

    def get_active_dwell_time(self, zone_id: str, current_timestamp: float) -> Optional[float]:
        """Get current live dwell time for an active zone visit."""
        visit = self.active_visits.get(zone_id)
        if visit is not None:
            return current_timestamp - visit.entry_time
        return None


class DwellTracker:
    """
    Manages dwell-time tracking for all active shoppers.

    Tracks zone presence using center-point polygon membership,
    handles gap tolerance for brief tracking interruptions,
    and supports overlapping zones.
    """

    def __init__(
        self,
        gap_tolerance: int = 15,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the dwell tracker.

        Parameters
        ----------
        gap_tolerance : int
            Number of frames a shopper can be missing from a zone
            before the visit is closed.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.gap_tolerance = gap_tolerance
        self.logger = logger or setup_logger("dwell_tracker")
        self._states: Dict[int, ShopperDwellState] = {}

    def update(
        self,
        track_id: int,
        frame: int,
        timestamp: float,
        current_zone_ids: List[str],
        zone_names: Dict[str, str],
        confidence: float,
    ) -> None:
        """
        Update dwell tracking for a single shopper in the current frame.

        Parameters
        ----------
        track_id : int
            Persistent tracking ID.
        frame : int
            Current frame number.
        timestamp : float
            Current video timestamp in seconds.
        current_zone_ids : List[str]
            List of zone IDs the shopper's center point is currently inside.
        zone_names : Dict[str, str]
            Mapping of zone_id -> zone_name for all configured zones.
        confidence : float
            Detection confidence for this frame.
        """
        if track_id not in self._states:
            self._states[track_id] = ShopperDwellState(track_id)

        state = self._states[track_id]
        state.last_seen_frame = frame
        current_set = set(current_zone_ids)

        # Determine active zones that the shopper has left
        active_zone_ids = state.get_active_zone_ids()

        # Zones the shopper has exited (was active but not currently present)
        exited_zones = active_zone_ids - current_set

        # Handle exited zones: apply gap tolerance
        for zone_id in exited_zones:
            if state.should_close_zone_visit(zone_id, frame, self.gap_tolerance):
                # Gap exceeded tolerance — close the visit
                last_seen = state._zone_last_seen.get(zone_id, frame)
                last_timestamp = timestamp - ((frame - last_seen) / max(1, frame)) * timestamp if frame > 0 else timestamp
                # Use the last-seen frame's estimated timestamp
                close_timestamp = state.active_visits[zone_id].entry_time + (
                    (last_seen - state.active_visits[zone_id].entry_frame)
                    * (timestamp / frame) if frame > 0 else 0
                )
                state.exit_zone(zone_id, last_seen, close_timestamp)

        # Zones the shopper has entered (not previously active)
        for zone_id in current_set:
            if zone_id not in state.active_visits:
                zone_name = zone_names.get(zone_id, zone_id)
                state.enter_zone(zone_id, zone_name, frame, timestamp)

        # Update presence for zones the shopper is still inside
        for zone_id in current_set & state.get_active_zone_ids():
            state.update_presence(zone_id, frame, confidence)

    def handle_lost_track(
        self, track_id: int, frame: int, timestamp: float
    ) -> List[DwellEvent]:
        """
        Handle a track that has been lost (disappeared without confirmed exit).

        Closes all active visits with 'track_lost' status.

        Parameters
        ----------
        track_id : int
            Tracking ID that disappeared.
        frame : int
            Last frame the track was seen.
        timestamp : float
            Timestamp of last detection.

        Returns
        -------
        List[DwellEvent]
            List of closed dwell events.
        """
        state = self._states.get(track_id)
        if state is None:
            return []
        return state.close_all_active(frame, timestamp, status="track_lost")

    def close_remaining_visits(
        self, frame: int, timestamp: float, status: str = "completed"
    ) -> None:
        """Close all remaining active visits across all shoppers."""
        for state in self._states.values():
            state.close_all_active(frame, timestamp, status=status)

    def get_state(self, track_id: int) -> Optional[ShopperDwellState]:
        """Get the dwell state for a specific shopper."""
        return self._states.get(track_id)

    def get_all_states(self) -> Dict[int, ShopperDwellState]:
        """Return all shopper dwell states."""
        return dict(self._states)

    def get_all_events(self) -> List[DwellEvent]:
        """Return all dwell events (completed + active) across all shoppers."""
        all_events = []
        for state in self._states.values():
            all_events.extend(state.get_all_events())
        return all_events

    def get_completed_events(self) -> List[DwellEvent]:
        """Return only completed dwell events."""
        events = []
        for state in self._states.values():
            events.extend(state.completed_visits)
        return events

    def get_active_visits(self) -> List[DwellEvent]:
        """Return all currently active visits."""
        active = []
        for state in self._states.values():
            active.extend(state.active_visits.values())
        return active

    def get_active_dwell_times(
        self, track_id: int, current_timestamp: float
    ) -> Dict[str, float]:
        """
        Get current live dwell times for all active zones of a shopper.

        Parameters
        ----------
        track_id : int
            Tracking ID.
        current_timestamp : float
            Current video timestamp.

        Returns
        -------
        Dict[str, float]
            zone_id -> current dwell time in seconds.
        """
        state = self._states.get(track_id)
        if state is None:
            return {}

        dwell_times = {}
        for zone_id in state.get_active_zone_ids():
            dt = state.get_active_dwell_time(zone_id, current_timestamp)
            if dt is not None:
                dwell_times[zone_id] = dt
        return dwell_times

    def get_current_zone_occupancy(self) -> Dict[str, int]:
        """Get number of shoppers currently dwelling in each zone."""
        occupancy: Dict[str, int] = {}
        for state in self._states.values():
            for zone_id in state.get_active_zone_ids():
                occupancy[zone_id] = occupancy.get(zone_id, 0) + 1
        return occupancy

    @property
    def total_completed_events(self) -> int:
        """Total number of completed dwell events."""
        return sum(
            len(s.completed_visits) for s in self._states.values()
        )

    @property
    def total_active_visits(self) -> int:
        """Total number of currently active visits."""
        return sum(
            len(s.active_visits) for s in self._states.values()
        )

    @property
    def total_track_lost_events(self) -> int:
        """Total number of track-lost events."""
        count = 0
        for state in self._states.values():
            for event in state.completed_visits:
                if event.status == "track_lost":
                    count += 1
        return count
