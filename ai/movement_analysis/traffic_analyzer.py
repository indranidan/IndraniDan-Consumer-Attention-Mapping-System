"""
Movement Analysis — Traffic Analyzer
=======================================
Generates traffic statistics from session, zone, and entry/exit data.
Computes per-zone visitor counts, zone transition matrices,
time-bucketed traffic, and overall summary metrics.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from ai.logger import setup_logger
from ai.movement_analysis.entry_exit_monitor import EntryExitMonitor
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_manager import ZoneManager
from ai.movement_analysis.zone_tracker import ZoneTracker


class TrafficAnalyzer:
    """
    Aggregates traffic statistics from all movement analysis components.
    """

    def __init__(
        self,
        zone_manager: ZoneManager,
        zone_tracker: ZoneTracker,
        entry_exit_monitor: EntryExitMonitor,
        session_manager: SessionManager,
        video_fps: float = 30.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.zone_manager = zone_manager
        self.zone_tracker = zone_tracker
        self.entry_exit_monitor = entry_exit_monitor
        self.session_manager = session_manager
        self.video_fps = video_fps
        self.logger = logger or setup_logger("traffic_analyzer")

        # Per-frame active shopper tracking for max/avg calculations
        self._frame_active_counts: List[int] = []

    def record_frame_active_count(self, count: int) -> None:
        """Record the number of active shoppers in a frame."""
        self._frame_active_counts.append(count)

    def generate_stats(self) -> Dict:
        """
        Generate comprehensive traffic statistics.

        Returns
        -------
        Dict
            Complete traffic summary suitable for JSON export.
        """
        self.logger.info("Generating traffic statistics...")

        sessions = self.session_manager.get_all_sessions()
        total_unique = len(sessions)

        # Max and average simultaneous shoppers
        max_simultaneous = max(self._frame_active_counts) if self._frame_active_counts else 0
        avg_active = (
            sum(self._frame_active_counts) / len(self._frame_active_counts)
            if self._frame_active_counts
            else 0.0
        )

        # Per-zone statistics
        zone_stats = self._compute_zone_stats()

        # Zone transition matrix
        transition_matrix = self._compute_transition_matrix()

        # Traffic by time period (1-minute buckets)
        time_buckets = self._compute_time_buckets()

        stats = {
            "total_unique_shoppers": total_unique,
            "total_entries": self.entry_exit_monitor.total_entries,
            "total_exits": self.entry_exit_monitor.total_exits,
            "total_track_lost": self.entry_exit_monitor.total_track_lost,
            "current_active_shoppers": self.session_manager.get_active_count(),
            "max_simultaneous_shoppers": max_simultaneous,
            "average_active_shoppers": round(avg_active, 2),
            "completed_sessions": self.session_manager.get_completed_count(),
            "track_lost_sessions": self.session_manager.get_track_lost_count(),
            "zone_statistics": zone_stats,
            "zone_transition_matrix": transition_matrix,
            "traffic_by_time_period": time_buckets,
        }

        self.logger.info(
            f"Traffic stats: {total_unique} unique shoppers, "
            f"{self.entry_exit_monitor.total_entries} entries, "
            f"{self.entry_exit_monitor.total_exits} exits"
        )

        return stats

    def _compute_zone_stats(self) -> List[Dict]:
        """Compute per-zone traffic statistics."""
        zone_stats = []
        visitor_counts = self.zone_tracker.get_per_zone_visitor_counts()

        for zone_def in self.zone_manager.get_all_zones():
            zone_id = zone_def.id

            # Count total visits (a single shopper can visit multiple times)
            total_visits = 0
            for state in self.zone_tracker.get_all_states().values():
                total_visits += sum(
                    1 for v in state.zone_visits if v.zone_id == zone_id
                )
                # Count active visits too
                if zone_id in state.active_visits:
                    total_visits += 1

            zone_stats.append({
                "zone_id": zone_id,
                "zone_name": zone_def.name,
                "unique_visitors": visitor_counts.get(zone_id, 0),
                "total_visits": total_visits,
            })

        return zone_stats

    def _compute_transition_matrix(self) -> Dict[str, Dict[str, int]]:
        """Compute zone-to-zone transition counts."""
        matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for state in self.zone_tracker.get_all_states().values():
            transitions = state.get_transition_sequence()
            for i in range(1, len(transitions)):
                from_zone = transitions[i - 1]
                to_zone = transitions[i]
                if from_zone != to_zone:
                    matrix[from_zone][to_zone] += 1

        # Convert defaultdict to regular dict for JSON
        return {k: dict(v) for k, v in matrix.items()}

    def _compute_time_buckets(self) -> List[Dict]:
        """Compute traffic by 1-minute time periods."""
        sessions = self.session_manager.get_all_sessions()
        if not sessions:
            return []

        max_time = max(
            (s.end_time for s in sessions if s.end_time is not None), default=0.0
        )

        if max_time <= 0:
            return []

        bucket_duration = 60.0  # 1-minute buckets
        num_buckets = int(max_time / bucket_duration) + 1
        buckets = []

        for i in range(num_buckets):
            bucket_start = i * bucket_duration
            bucket_end = (i + 1) * bucket_duration

            active_in_bucket = 0
            for session in sessions:
                s_start = session.start_time
                s_end = session.end_time if session.end_time is not None else max_time

                if s_start < bucket_end and s_end > bucket_start:
                    active_in_bucket += 1

            mins = int(bucket_start // 60)
            secs = int(bucket_start % 60)

            buckets.append({
                "period": f"{mins:02d}:{secs:02d}-{int(bucket_end // 60):02d}:{int(bucket_end % 60):02d}",
                "start_time": round(bucket_start, 1),
                "end_time": round(bucket_end, 1),
                "active_shoppers": active_in_bucket,
            })

        return buckets
