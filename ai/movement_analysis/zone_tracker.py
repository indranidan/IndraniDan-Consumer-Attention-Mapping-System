"""
Movement Analysis — Zone Tracker
===================================
Tracks per-shopper zone presence, detects zone entries/exits,
and records zone transitions in chronological order.
Uses ZoneManager for spatial polygon queries.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ai.logger import setup_logger
from ai.movement_analysis.zone_manager import ZoneManager


@dataclass
class ZoneVisit:
    """Record of a shopper's visit to a specific zone."""

    zone_id: str
    zone_name: str
    entry_frame: int
    entry_time: float
    exit_frame: Optional[int] = None
    exit_time: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.exit_time is not None and self.entry_time is not None:
            return round(self.exit_time - self.entry_time, 3)
        return None

    def to_dict(self) -> Dict:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "entry_frame": self.entry_frame,
            "entry_time": round(self.entry_time, 3),
            "exit_frame": self.exit_frame,
            "exit_time": round(self.exit_time, 3) if self.exit_time is not None else None,
            "duration": self.duration,
        }


class ShopperZoneState:
    """Manages zone presence state for a single tracked shopper."""

    def __init__(self, track_id: int):
        self.track_id = track_id
        self.current_zones: Set[str] = set()
        self.zone_visits: List[ZoneVisit] = []
        self.active_visits: Dict[str, ZoneVisit] = {}
        self.zone_transitions: List[Tuple[str, float]] = []
        self.zones_visited: Set[str] = set()

    def enter_zone(self, zone_id: str, zone_name: str, frame: int, timestamp: float) -> None:
        self.current_zones.add(zone_id)
        self.zones_visited.add(zone_id)
        visit = ZoneVisit(zone_id=zone_id, zone_name=zone_name, entry_frame=frame, entry_time=timestamp)
        self.active_visits[zone_id] = visit
        self.zone_transitions.append((zone_id, timestamp))

    def exit_zone(self, zone_id: str, frame: int, timestamp: float) -> None:
        self.current_zones.discard(zone_id)
        if zone_id in self.active_visits:
            visit = self.active_visits.pop(zone_id)
            visit.exit_frame = frame
            visit.exit_time = timestamp
            self.zone_visits.append(visit)

    def close_all_active(self, frame: int, timestamp: float) -> None:
        for zone_id in list(self.active_visits.keys()):
            self.exit_zone(zone_id, frame, timestamp)

    def get_all_visits(self) -> List[ZoneVisit]:
        return list(self.zone_visits)

    def get_current_zone_names(self, zone_manager: ZoneManager) -> List[str]:
        return [zone_manager.get_zone_name(zid) for zid in self.current_zones]

    def get_transition_sequence(self) -> List[str]:
        return [zone_id for zone_id, _ in self.zone_transitions]

    def get_transitions_with_timestamps(self) -> List[Dict]:
        return [{"zone_id": zid, "timestamp": round(ts, 3)} for zid, ts in self.zone_transitions]


class ZoneTracker:
    """Tracks zone presence for all active shoppers."""

    def __init__(self, zone_manager: ZoneManager, logger: Optional[logging.Logger] = None):
        self.zone_manager = zone_manager
        self.logger = logger or setup_logger("zone_tracker")
        self._states: Dict[int, ShopperZoneState] = {}

    def update(self, track_id: int, frame: int, timestamp: float, center_x: int, center_y: int) -> List[str]:
        if track_id not in self._states:
            self._states[track_id] = ShopperZoneState(track_id)

        state = self._states[track_id]
        current_zone_ids = set(self.zone_manager.get_zones_for_point(center_x, center_y))

        exited_zones = state.current_zones - current_zone_ids
        for zone_id in exited_zones:
            state.exit_zone(zone_id, frame, timestamp)

        entered_zones = current_zone_ids - state.current_zones
        for zone_id in entered_zones:
            zone_name = self.zone_manager.get_zone_name(zone_id)
            state.enter_zone(zone_id, zone_name, frame, timestamp)

        return list(current_zone_ids)

    def close_track(self, track_id: int, frame: int, timestamp: float) -> None:
        state = self._states.get(track_id)
        if state:
            state.close_all_active(frame, timestamp)

    def get_state(self, track_id: int) -> Optional[ShopperZoneState]:
        return self._states.get(track_id)

    def get_all_states(self) -> Dict[int, ShopperZoneState]:
        return dict(self._states)

    def get_current_zone_names(self, track_id: int) -> List[str]:
        state = self._states.get(track_id)
        if state:
            return state.get_current_zone_names(self.zone_manager)
        return []

    def get_per_zone_visitor_counts(self) -> Dict[str, int]:
        zone_counts: Dict[str, int] = {zid: 0 for zid in self.zone_manager.get_all_zone_ids()}
        for state in self._states.values():
            for zone_id in state.zones_visited:
                if zone_id in zone_counts:
                    zone_counts[zone_id] += 1
        return zone_counts

    def get_all_zone_visits(self) -> List[Dict]:
        all_visits = []
        for track_id, state in sorted(self._states.items()):
            for visit in state.zone_visits:
                record = visit.to_dict()
                record["tracking_id"] = track_id
                all_visits.append(record)
        return all_visits

    def get_current_zone_occupancy(self) -> Dict[str, int]:
        occupancy: Dict[str, int] = {zid: 0 for zid in self.zone_manager.get_all_zone_ids()}
        for state in self._states.values():
            for zone_id in state.current_zones:
                if zone_id in occupancy:
                    occupancy[zone_id] += 1
        return occupancy
