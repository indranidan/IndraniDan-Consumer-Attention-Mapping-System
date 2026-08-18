"""
Dwell-Time Analysis — Dwell Aggregator
=========================================
Statistical aggregation engine for dwell-time data.
Computes per-zone summaries, per-shopper summaries,
and configurable dwell-time distribution buckets.
"""

import logging
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ai.logger import setup_logger
from ai.dwell_time_analysis.dwell_tracker import DwellEvent, DwellTracker
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_manager import ZoneManager


@dataclass
class ZoneDwellSummary:
    """Aggregated dwell statistics for a single zone (Phase 4.7)."""

    zone_id: str
    zone_name: str
    unique_shoppers: int = 0
    total_visits: int = 0
    completed_visits: int = 0
    track_lost_visits: int = 0
    total_dwell_seconds: float = 0.0
    average_dwell_seconds: float = 0.0
    median_dwell_seconds: float = 0.0
    min_dwell_seconds: float = 0.0
    max_dwell_seconds: float = 0.0
    current_active_shoppers: int = 0

    def to_dict(self) -> Dict:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "unique_shoppers": self.unique_shoppers,
            "total_visits": self.total_visits,
            "completed_visits": self.completed_visits,
            "track_lost_visits": self.track_lost_visits,
            "total_dwell_seconds": round(self.total_dwell_seconds, 3),
            "average_dwell_seconds": round(self.average_dwell_seconds, 3),
            "median_dwell_seconds": round(self.median_dwell_seconds, 3),
            "min_dwell_seconds": round(self.min_dwell_seconds, 3),
            "max_dwell_seconds": round(self.max_dwell_seconds, 3),
            "current_active_shoppers": self.current_active_shoppers,
        }


@dataclass
class ShopperDwellSummary:
    """Aggregated dwell statistics for a single shopper (Phase 4.8)."""

    tracking_id: int
    session_duration: Optional[float] = None
    session_status: str = "unknown"
    zones_visited: int = 0
    total_zone_visits: int = 0
    total_observed_dwell_seconds: float = 0.0
    average_zone_dwell_seconds: float = 0.0
    longest_zone_visit_seconds: float = 0.0
    zone_with_longest_dwell: str = ""
    zone_name_with_longest_dwell: str = ""

    def to_dict(self) -> Dict:
        return {
            "tracking_id": self.tracking_id,
            "session_duration": round(self.session_duration, 3) if self.session_duration is not None else None,
            "session_status": self.session_status,
            "zones_visited": self.zones_visited,
            "total_zone_visits": self.total_zone_visits,
            "total_observed_dwell_seconds": round(self.total_observed_dwell_seconds, 3),
            "average_zone_dwell_seconds": round(self.average_zone_dwell_seconds, 3),
            "longest_zone_visit_seconds": round(self.longest_zone_visit_seconds, 3),
            "zone_with_longest_dwell": self.zone_with_longest_dwell,
            "zone_name_with_longest_dwell": self.zone_name_with_longest_dwell,
        }


@dataclass
class DwellDistributionBucket:
    """A single bucket in the dwell-time distribution."""

    label: str
    min_seconds: float
    max_seconds: Optional[float]
    visit_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "min_seconds": self.min_seconds,
            "max_seconds": self.max_seconds,
            "visit_count": self.visit_count,
        }


@dataclass
class DwellDistribution:
    """Complete dwell-time distribution analysis (Phase 4.9)."""

    buckets: List[DwellDistributionBucket] = field(default_factory=list)
    total_visits_counted: int = 0

    def to_dict(self) -> Dict:
        return {
            "total_visits_counted": self.total_visits_counted,
            "buckets": [b.to_dict() for b in self.buckets],
        }


class DwellAggregator:
    """
    Aggregates dwell-time data into summaries and distributions.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or setup_logger("dwell_aggregator")

    def aggregate_zones(
        self,
        dwell_tracker: DwellTracker,
        zone_manager: ZoneManager,
    ) -> List[ZoneDwellSummary]:
        """
        Compute per-zone dwell statistics (Phase 4.7).

        Parameters
        ----------
        dwell_tracker : DwellTracker
            Dwell tracker with completed/active events.
        zone_manager : ZoneManager
            Zone manager for zone metadata.

        Returns
        -------
        List[ZoneDwellSummary]
            Per-zone aggregated statistics.
        """
        self.logger.info("Aggregating zone dwell statistics...")

        all_events = dwell_tracker.get_all_events()
        active_occupancy = dwell_tracker.get_current_zone_occupancy()

        # Group events by zone
        zone_events: Dict[str, List[DwellEvent]] = {}
        for zone_def in zone_manager.get_all_zones():
            zone_events[zone_def.id] = []

        for event in all_events:
            if event.zone_id in zone_events:
                zone_events[event.zone_id].append(event)
            else:
                zone_events[event.zone_id] = [event]

        summaries = []
        for zone_def in zone_manager.get_all_zones():
            zone_id = zone_def.id
            events = zone_events.get(zone_id, [])

            summary = ZoneDwellSummary(
                zone_id=zone_id,
                zone_name=zone_def.name,
                current_active_shoppers=active_occupancy.get(zone_id, 0),
            )

            if not events:
                summaries.append(summary)
                continue

            # Unique shoppers
            unique_ids = set(e.tracking_id for e in events)
            summary.unique_shoppers = len(unique_ids)
            summary.total_visits = len(events)

            # Separate completed and track-lost
            completed = [e for e in events if e.status == "completed"]
            track_lost = [e for e in events if e.status == "track_lost"]
            summary.completed_visits = len(completed)
            summary.track_lost_visits = len(track_lost)

            # Dwell time stats (use events with dwell_seconds available)
            dwell_durations = [
                e.dwell_seconds for e in events
                if e.dwell_seconds is not None and e.dwell_seconds >= 0
            ]

            if dwell_durations:
                summary.total_dwell_seconds = sum(dwell_durations)
                summary.average_dwell_seconds = summary.total_dwell_seconds / len(dwell_durations)
                summary.median_dwell_seconds = statistics.median(dwell_durations)
                summary.min_dwell_seconds = min(dwell_durations)
                summary.max_dwell_seconds = max(dwell_durations)

            summaries.append(summary)

        self.logger.info(f"Zone dwell aggregation complete: {len(summaries)} zones")
        return summaries

    def aggregate_shoppers(
        self,
        dwell_tracker: DwellTracker,
        session_manager: SessionManager,
    ) -> List[ShopperDwellSummary]:
        """
        Compute per-shopper dwell statistics (Phase 4.8).

        Parameters
        ----------
        dwell_tracker : DwellTracker
            Dwell tracker with completed/active events.
        session_manager : SessionManager
            Session manager for session duration.

        Returns
        -------
        List[ShopperDwellSummary]
            Per-shopper aggregated statistics.
        """
        self.logger.info("Aggregating shopper dwell statistics...")

        summaries = []

        for track_id, state in sorted(dwell_tracker.get_all_states().items()):
            all_events = state.get_all_events()

            summary = ShopperDwellSummary(tracking_id=track_id)

            # Session info from Phase 3
            session = session_manager.get_session(track_id)
            if session is not None:
                summary.session_status = session.status
                if session.end_time is not None and session.start_time is not None:
                    summary.session_duration = session.end_time - session.start_time

            if not all_events:
                summaries.append(summary)
                continue

            # Unique zones visited
            unique_zones = set(e.zone_id for e in all_events)
            summary.zones_visited = len(unique_zones)
            summary.total_zone_visits = len(all_events)

            # Dwell time stats
            dwell_durations = [
                e.dwell_seconds for e in all_events
                if e.dwell_seconds is not None and e.dwell_seconds >= 0
            ]

            if dwell_durations:
                summary.total_observed_dwell_seconds = sum(dwell_durations)
                summary.average_zone_dwell_seconds = (
                    summary.total_observed_dwell_seconds / len(dwell_durations)
                )
                summary.longest_zone_visit_seconds = max(dwell_durations)

                # Find zone with longest dwell
                longest_event = max(
                    [e for e in all_events if e.dwell_seconds is not None],
                    key=lambda e: e.dwell_seconds,
                )
                summary.zone_with_longest_dwell = longest_event.zone_id
                summary.zone_name_with_longest_dwell = longest_event.zone_name

            summaries.append(summary)

        self.logger.info(f"Shopper dwell aggregation complete: {len(summaries)} shoppers")
        return summaries

    def compute_distribution(
        self,
        dwell_tracker: DwellTracker,
        bucket_boundaries: List[int],
    ) -> DwellDistribution:
        """
        Compute dwell-time distribution across configurable buckets (Phase 4.9).

        Parameters
        ----------
        dwell_tracker : DwellTracker
            Dwell tracker with completed events.
        bucket_boundaries : List[int]
            Sorted list of bucket boundary values in seconds.
            Example: [10, 30, 60, 120] creates buckets:
            0-10s, 10-30s, 30-60s, 60-120s, 120+s

        Returns
        -------
        DwellDistribution
            Distribution analysis with bucket counts.
        """
        self.logger.info("Computing dwell-time distribution...")

        boundaries = sorted(bucket_boundaries)
        buckets: List[DwellDistributionBucket] = []

        # Create bucket objects
        # First bucket: 0 to first boundary
        if boundaries:
            buckets.append(DwellDistributionBucket(
                label=f"0–{boundaries[0]}s",
                min_seconds=0.0,
                max_seconds=float(boundaries[0]),
            ))

            # Middle buckets
            for i in range(1, len(boundaries)):
                buckets.append(DwellDistributionBucket(
                    label=f"{boundaries[i-1]}–{boundaries[i]}s",
                    min_seconds=float(boundaries[i - 1]),
                    max_seconds=float(boundaries[i]),
                ))

            # Last bucket: last boundary to infinity
            buckets.append(DwellDistributionBucket(
                label=f"{boundaries[-1]}+s",
                min_seconds=float(boundaries[-1]),
                max_seconds=None,
            ))

        # Count events into buckets
        all_events = dwell_tracker.get_all_events()
        total_counted = 0

        for event in all_events:
            dwell = event.dwell_seconds
            if dwell is None or dwell < 0:
                continue

            total_counted += 1
            for bucket in buckets:
                if bucket.max_seconds is None:
                    # Open-ended bucket (last)
                    if dwell >= bucket.min_seconds:
                        bucket.visit_count += 1
                        break
                else:
                    if bucket.min_seconds <= dwell < bucket.max_seconds:
                        bucket.visit_count += 1
                        break

        distribution = DwellDistribution(
            buckets=buckets,
            total_visits_counted=total_counted,
        )

        self.logger.info(f"Distribution computed: {total_counted} visits across {len(buckets)} buckets")
        return distribution
