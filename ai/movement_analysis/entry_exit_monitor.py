"""
Movement Analysis — Entry/Exit Monitor
=========================================
Detects when tracked shoppers cross entry and exit regions.
Prevents duplicate counting per tracking ID.
Distinguishes between explicit exits and track-lost events.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from ai.logger import setup_logger
from ai.movement_analysis.zone_manager import ZoneManager


@dataclass
class EntryExitEvent:
    """Record of a shopper entering or exiting the store."""

    track_id: int
    region_id: str
    region_name: str
    event_type: str  # "entry" or "exit"
    frame: int
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "track_id": self.track_id,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "event_type": self.event_type,
            "frame": self.frame,
            "timestamp": round(self.timestamp, 3),
        }


class EntryExitMonitor:
    """
    Monitors entry and exit regions for tracked shoppers.
    Ensures each tracking ID is counted only once for entry and once for exit.
    """

    def __init__(self, zone_manager: ZoneManager, logger: Optional[logging.Logger] = None):
        self.zone_manager = zone_manager
        self.logger = logger or setup_logger("entry_exit_monitor")

        self.entered_ids: Set[int] = set()
        self.exited_ids: Set[int] = set()
        self.track_lost_ids: Set[int] = set()

        self.entry_events: List[EntryExitEvent] = []
        self.exit_events: List[EntryExitEvent] = []

        # Track entry timestamps per ID
        self.entry_timestamps: Dict[int, float] = {}
        self.exit_timestamps: Dict[int, float] = {}

    def update(self, track_id: int, frame: int, timestamp: float, center_x: int, center_y: int) -> Optional[EntryExitEvent]:
        """
        Check if a tracked shopper has crossed an entry or exit region.

        Returns
        -------
        Optional[EntryExitEvent]
            Event if an entry or exit was detected, else None.
        """
        event = None

        # Check entry regions (only if not already entered)
        if track_id not in self.entered_ids:
            entry_region_id = self.zone_manager.is_in_entry_region(center_x, center_y)
            if entry_region_id:
                region_def = self.zone_manager.entry_regions[entry_region_id]
                event = EntryExitEvent(
                    track_id=track_id,
                    region_id=entry_region_id,
                    region_name=region_def.name,
                    event_type="entry",
                    frame=frame,
                    timestamp=timestamp,
                )
                self.entered_ids.add(track_id)
                self.entry_events.append(event)
                self.entry_timestamps[track_id] = timestamp
                return event

        # Check exit regions (only if not already exited)
        if track_id not in self.exited_ids:
            exit_region_id = self.zone_manager.is_in_exit_region(center_x, center_y)
            if exit_region_id:
                region_def = self.zone_manager.exit_regions[exit_region_id]
                event = EntryExitEvent(
                    track_id=track_id,
                    region_id=exit_region_id,
                    region_name=region_def.name,
                    event_type="exit",
                    frame=frame,
                    timestamp=timestamp,
                )
                self.exited_ids.add(track_id)
                self.exit_events.append(event)
                self.exit_timestamps[track_id] = timestamp
                return event

        return None

    def mark_track_lost(self, track_id: int, frame: int, timestamp: float) -> None:
        """
        Mark a track as lost (disappeared without crossing exit region).

        Parameters
        ----------
        track_id : int
            Tracking ID that disappeared.
        frame : int
            Last frame the track was seen.
        timestamp : float
            Timestamp of last detection.
        """
        if track_id not in self.exited_ids:
            self.track_lost_ids.add(track_id)

    def get_entry_time(self, track_id: int) -> Optional[float]:
        """Get the entry timestamp for a track, if detected."""
        return self.entry_timestamps.get(track_id)

    def get_exit_time(self, track_id: int) -> Optional[float]:
        """Get the exit timestamp for a track, if detected."""
        return self.exit_timestamps.get(track_id)

    def has_entered(self, track_id: int) -> bool:
        """Check if a track has been detected entering."""
        return track_id in self.entered_ids

    def has_exited(self, track_id: int) -> bool:
        """Check if a track has been detected exiting."""
        return track_id in self.exited_ids

    def is_track_lost(self, track_id: int) -> bool:
        """Check if a track was lost without detected exit."""
        return track_id in self.track_lost_ids

    @property
    def total_entries(self) -> int:
        return len(self.entered_ids)

    @property
    def total_exits(self) -> int:
        return len(self.exited_ids)

    @property
    def total_track_lost(self) -> int:
        return len(self.track_lost_ids)

    def get_all_events(self) -> List[Dict]:
        """Return all entry/exit events sorted by timestamp."""
        all_events = self.entry_events + self.exit_events
        all_events.sort(key=lambda e: e.timestamp)
        return [e.to_dict() for e in all_events]
