"""
Movement Analysis — Session Manager
======================================
Creates and manages shopper sessions. Each unique tracking ID
gets a session containing path, zones visited, transitions,
entry/exit times, and journey timeline.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ai.logger import setup_logger
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.zone_tracker import ZoneTracker


@dataclass
class ShopperSession:
    """Complete session record for a tracked shopper."""

    session_id: str
    tracking_id: int
    start_frame: int
    start_time: float
    end_frame: Optional[int] = None
    end_time: Optional[float] = None
    entry_time: Optional[float] = None
    exit_time: Optional[float] = None
    status: str = "active"  # "active", "completed", "track_lost"
    zones_visited: List[str] = field(default_factory=list)
    zone_transitions: List[Dict] = field(default_factory=list)
    frames_tracked: int = 0
    total_confidence: float = 0.0
    num_confidence_samples: int = 0
    journey: List[Dict] = field(default_factory=list)

    @property
    def average_confidence(self) -> float:
        if self.num_confidence_samples > 0:
            return self.total_confidence / self.num_confidence_samples
        return 0.0

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "tracking_id": self.tracking_id,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3) if self.end_time is not None else None,
            "entry_time": round(self.entry_time, 3) if self.entry_time is not None else None,
            "exit_time": round(self.exit_time, 3) if self.exit_time is not None else None,
            "status": self.status,
            "zones_visited": self.zones_visited,
            "zone_transitions": self.zone_transitions,
            "frames_tracked": self.frames_tracked,
            "average_confidence": round(self.average_confidence, 4),
            "journey": self.journey,
        }


def _format_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS display string."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


class SessionManager:
    """
    Manages shopper session lifecycle for all tracked people.
    Creates sessions on first detection, updates with analytics data,
    and finalizes with proper status determination.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or setup_logger("session_manager")
        self._sessions: Dict[int, ShopperSession] = {}
        self._session_counter: int = 0

    def get_or_create_session(self, track_id: int, frame: int, timestamp: float) -> ShopperSession:
        """Get existing session or create a new one for a tracking ID."""
        if track_id not in self._sessions:
            self._session_counter += 1
            session_id = f"session_{self._session_counter:03d}"
            self._sessions[track_id] = ShopperSession(
                session_id=session_id,
                tracking_id=track_id,
                start_frame=frame,
                start_time=timestamp,
            )
        return self._sessions[track_id]

    def update_session(self, track_id: int, frame: int, timestamp: float, confidence: float) -> None:
        """Update session tracking stats for a frame."""
        session = self.get_or_create_session(track_id, frame, timestamp)
        session.end_frame = frame
        session.end_time = timestamp
        session.frames_tracked += 1
        session.total_confidence += confidence
        session.num_confidence_samples += 1

    def finalize_all(
        self,
        path_tracker: PathTracker,
        zone_tracker: ZoneTracker,
        entry_exit_monitor: EntryExitMonitor,
    ) -> None:
        """
        Finalize all sessions with complete analytics data.
        Sets status, builds journey, and populates zone/path information.
        """
        self.logger.info(f"Finalizing {len(self._sessions)} shopper sessions...")

        for track_id, session in self._sessions.items():
            # Set entry/exit timestamps
            session.entry_time = entry_exit_monitor.get_entry_time(track_id)
            session.exit_time = entry_exit_monitor.get_exit_time(track_id)

            # Determine session status
            if entry_exit_monitor.has_exited(track_id):
                session.status = "completed"
            elif entry_exit_monitor.is_track_lost(track_id):
                session.status = "track_lost"
            else:
                session.status = "track_lost"

            # Populate zones visited
            zone_state = zone_tracker.get_state(track_id)
            if zone_state:
                session.zones_visited = list(zone_state.zones_visited)
                session.zone_transitions = zone_state.get_transitions_with_timestamps()

            # Build journey timeline
            session.journey = self._build_journey(
                track_id, session, zone_state, entry_exit_monitor
            )

        self.logger.info("Session finalization complete.")

    def _build_journey(
        self,
        track_id: int,
        session: ShopperSession,
        zone_state,
        entry_exit_monitor: EntryExitMonitor,
    ) -> List[Dict]:
        """Build a chronological journey for a shopper."""
        events = []

        # Add entry event
        if session.entry_time is not None:
            events.append({
                "event": "entry",
                "location": "entrance",
                "timestamp": round(session.entry_time, 3),
                "display_time": _format_timestamp(session.entry_time),
            })

        # Add zone transitions
        if zone_state:
            for zone_id, ts in zone_state.zone_transitions:
                zone_name = zone_state.zone_visits[0].zone_name if zone_state.zone_visits else zone_id
                # Find the zone name from visits
                for v in zone_state.zone_visits:
                    if v.zone_id == zone_id:
                        zone_name = v.zone_name
                        break
                else:
                    # Check active visits
                    if zone_id in zone_state.active_visits:
                        zone_name = zone_state.active_visits[zone_id].zone_name

                events.append({
                    "event": "zone_visit",
                    "location": zone_id,
                    "zone_name": zone_name,
                    "timestamp": round(ts, 3),
                    "display_time": _format_timestamp(ts),
                })

        # Add exit event
        if session.exit_time is not None:
            events.append({
                "event": "exit",
                "location": "exit",
                "timestamp": round(session.exit_time, 3),
                "display_time": _format_timestamp(session.exit_time),
            })
        elif session.end_time is not None and session.status == "track_lost":
            events.append({
                "event": "track_lost",
                "location": "unknown",
                "timestamp": round(session.end_time, 3),
                "display_time": _format_timestamp(session.end_time),
            })

        # Sort by timestamp
        events.sort(key=lambda e: e["timestamp"])
        return events

    def get_session(self, track_id: int) -> Optional[ShopperSession]:
        return self._sessions.get(track_id)

    def get_all_sessions(self) -> List[ShopperSession]:
        return sorted(self._sessions.values(), key=lambda s: s.tracking_id)

    def get_all_sessions_dicts(self) -> List[Dict]:
        return [s.to_dict() for s in self.get_all_sessions()]

    def get_active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "active")

    def get_completed_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "completed")

    def get_track_lost_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "track_lost")
