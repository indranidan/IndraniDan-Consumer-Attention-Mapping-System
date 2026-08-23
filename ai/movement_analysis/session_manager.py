"""
Movement Analysis — Session Manager
======================================
Creates and manages shopper sessions. Each unique tracking ID
gets a session containing path, zones visited, transitions,
entry/exit times, and journey timeline.
"""

import logging
import math
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    status: str = "active"  # "active", "completed", "track_lost", "transient_noise"
    zones_visited: List[str] = field(default_factory=list)
    zone_transitions: List[Dict] = field(default_factory=list)
    frames_tracked: int = 0
    total_confidence: float = 0.0
    num_confidence_samples: int = 0
    journey: List[Dict] = field(default_factory=list)
    last_position: Optional[Tuple[int, int]] = None
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    stitched_track_ids: List[int] = field(default_factory=list)

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
            "stitched_track_ids": self.stitched_track_ids,
        }


def _format_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS display string."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


class SessionManager:
    """
    Manages shopper session lifecycle for all tracked people.
    Supports trajectory stitching across brief tracking dropouts and
    prunes transient noise tracks (<15 frames) from final analytics.
    """

    def __init__(
        self,
        stitching_max_time_sec: float = 3.0,
        stitching_max_distance_px: float = 180.0,
        min_lifetime_frames: int = 1,
        logger: Optional[logging.Logger] = None,
    ):
        self.stitching_max_time_sec = stitching_max_time_sec
        self.stitching_max_distance_px = stitching_max_distance_px
        self.min_lifetime_frames = min_lifetime_frames
        self.logger = logger or setup_logger("session_manager")
        self._sessions: Dict[int, ShopperSession] = {}
        self._track_aliases: Dict[int, int] = {}
        self._session_counter: int = 0

    def _resolve_canonical_id(self, track_id: int) -> int:
        """Resolve a potentially stitched track ID to its root session ID."""
        curr = track_id
        while curr in self._track_aliases:
            curr = self._track_aliases[curr]
        return curr

    def _find_stitching_match(
        self,
        frame: int,
        timestamp: float,
        position: Optional[Tuple[int, int]] = None,
    ) -> Optional[ShopperSession]:
        """Find an inactive session that can be stitched with a newly appearing track."""
        if position is None:
            return None

        best_session = None
        min_dist = float("inf")

        for session in self._sessions.values():
            if session.end_time is None or session.last_position is None:
                continue

            dt = timestamp - session.end_time
            if 0.0 < dt <= self.stitching_max_time_sec:
                dx = position[0] - session.last_position[0]
                dy = position[1] - session.last_position[1]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist <= self.stitching_max_distance_px and dist < min_dist:
                    min_dist = dist
                    best_session = session

        return best_session

    def get_or_create_session(
        self,
        track_id: int,
        frame: int,
        timestamp: float,
        position: Optional[Tuple[int, int]] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> ShopperSession:
        """Get existing session or create/stitch a new one for a tracking ID."""
        canonical_id = self._resolve_canonical_id(track_id)
        if canonical_id in self._sessions:
            return self._sessions[canonical_id]

        # Attempt spatial-temporal stitching with a recently lost session
        stitching_target = self._find_stitching_match(frame, timestamp, position)
        if stitching_target is not None:
            self._track_aliases[track_id] = stitching_target.tracking_id
            stitching_target.stitched_track_ids.append(track_id)
            self.logger.info(
                f"Stitched fragmented track {track_id} into session {stitching_target.session_id} "
                f"(canonical track {stitching_target.tracking_id})"
            )
            return stitching_target

        # Create brand new session
        self._session_counter += 1
        session_id = f"session_{self._session_counter:03d}"
        session = ShopperSession(
            session_id=session_id,
            tracking_id=track_id,
            start_frame=frame,
            start_time=timestamp,
            last_position=position,
            last_bbox=bbox,
        )
        self._sessions[track_id] = session
        return session

    def update_session(
        self,
        track_id: int,
        frame: int,
        timestamp: float,
        confidence: float,
        position: Optional[Tuple[int, int]] = None,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        """Update session tracking stats and last observed position for a frame."""
        session = self.get_or_create_session(track_id, frame, timestamp, position, bbox)
        session.end_frame = frame
        session.end_time = timestamp
        session.frames_tracked += 1
        session.total_confidence += confidence
        session.num_confidence_samples += 1
        if position is not None:
            session.last_position = position
        if bbox is not None:
            session.last_bbox = bbox

    def finalize_all(
        self,
        path_tracker: PathTracker,
        zone_tracker: ZoneTracker,
        entry_exit_monitor: EntryExitMonitor,
        min_frames: Optional[int] = None,
    ) -> None:
        """
        Finalize all sessions with complete analytics data.
        Sets status, builds journey, populates zone/path info, and flags transient noise.
        """
        cutoff_frames = min_frames if min_frames is not None else self.min_lifetime_frames
        self.logger.info(f"Finalizing {len(self._sessions)} shopper sessions (min_frames={cutoff_frames})...")

        for track_id, session in self._sessions.items():
            # Set entry/exit timestamps
            session.entry_time = entry_exit_monitor.get_entry_time(track_id)
            session.exit_time = entry_exit_monitor.get_exit_time(track_id)

            # Determine session status
            if entry_exit_monitor.has_exited(track_id):
                session.status = "completed"
            elif entry_exit_monitor.is_track_lost(track_id):
                session.status = "track_lost"
            elif cutoff_frames > 1 and session.frames_tracked < cutoff_frames and session.num_confidence_samples < 5:
                session.status = "transient_noise"
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
        canonical_id = self._resolve_canonical_id(track_id)
        return self._sessions.get(canonical_id)

    def get_all_sessions(self, include_transient: bool = False) -> List[ShopperSession]:
        """Get all sessions, optionally filtering out transient noise."""
        if not include_transient:
            confirmed = [s for s in self._sessions.values() if s.status != "transient_noise"]
            if confirmed or not self._sessions:
                return sorted(confirmed, key=lambda s: s.tracking_id)
        return sorted(self._sessions.values(), key=lambda s: s.tracking_id)

    def get_all_sessions_dicts(self, include_transient: bool = False) -> List[Dict]:
        return [s.to_dict() for s in self.get_all_sessions(include_transient=include_transient)]

    def get_confirmed_count(self) -> int:
        return len(self.get_all_sessions(include_transient=False))

    def get_active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "active")

    def get_completed_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "completed")

    def get_track_lost_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "track_lost")
