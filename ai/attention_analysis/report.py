"""
Attention Analysis — Report Generator
=========================================
Generates Phase 5 attention analysis reports:
- attention_events.json
- shopper_attention_summary.json
- target_attention_summary.json
- attention_report.md

All values are clearly labeled as estimated attention (head orientation).
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ai.attention_analysis.attention_region_manager import AttentionRegionManager
from ai.attention_analysis.attention_tracker import AttentionTracker, AttentionEvent
from ai.logger import setup_logger
from ai.utils import ensure_directory


@dataclass
class ShopperAttentionSummary:
    """Per-shopper attention statistics."""
    tracking_id: int
    session_duration: float
    attention_event_count: int
    total_estimated_attention_sec: float
    average_attention_sec: float
    longest_attention_sec: float
    most_attended_target: str
    unknown_observation_count: int
    total_observations: int

    def to_dict(self) -> dict:
        return {
            "tracking_id": self.tracking_id,
            "session_duration_sec": round(self.session_duration, 2),
            "attention_event_count": self.attention_event_count,
            "total_estimated_attention_sec": round(self.total_estimated_attention_sec, 2),
            "average_attention_sec": round(self.average_attention_sec, 2),
            "longest_attention_sec": round(self.longest_attention_sec, 2),
            "most_attended_target": self.most_attended_target,
            "unknown_observation_count": self.unknown_observation_count,
            "total_observations": self.total_observations,
        }


@dataclass
class TargetAttentionSummary:
    """Per-target attention statistics."""
    target_id: str
    target_name: str
    target_type: str
    unique_shoppers: int
    attention_event_count: int
    total_attention_sec: float
    average_attention_sec: float
    maximum_attention_sec: float

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "unique_shoppers": self.unique_shoppers,
            "attention_event_count": self.attention_event_count,
            "total_attention_sec": round(self.total_attention_sec, 2),
            "average_attention_sec": round(self.average_attention_sec, 2),
            "maximum_attention_sec": round(self.maximum_attention_sec, 2),
        }


class AttentionReportGenerator:
    """Generates attention analysis report files."""

    def __init__(self, reports_dir: Path, logger: Optional[logging.Logger] = None):
        self.reports_dir = reports_dir
        self.logger = logger or setup_logger("attention_report")
        ensure_directory(self.reports_dir)

    def generate(
        self,
        processing_stats: dict,
        attention_tracker: AttentionTracker,
        region_manager: AttentionRegionManager,
        session_manager=None,
    ) -> None:
        """Generate all Phase 5 reports."""
        all_events = attention_tracker.get_all_events()
        self._write_events_json(all_events)

        shopper_summaries = self._compute_shopper_summaries(
            attention_tracker, session_manager
        )
        self._write_shopper_summary_json(shopper_summaries)

        target_summaries = self._compute_target_summaries(all_events, region_manager)
        self._write_target_summary_json(target_summaries)

        self._write_markdown_report(
            processing_stats, all_events, shopper_summaries, target_summaries
        )
        self.logger.info(f"Attention reports generated in: {self.reports_dir}")

    def _write_events_json(self, events: List[AttentionEvent]) -> None:
        path = self.reports_dir / "attention_events.json"
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_events": len(events),
            "note": "All attention values are estimated based on head orientation, not eye gaze.",
            "events": [e.to_dict() for e in events],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"  → {path.name}: {len(events)} events")

    def _compute_shopper_summaries(
        self, tracker: AttentionTracker, session_manager=None,
    ) -> List[ShopperAttentionSummary]:
        summaries = []
        track_ids = list(tracker.all_track_ids)

        if session_manager:
            confirmed_sessions = session_manager.get_all_sessions(include_transient=False)
            if confirmed_sessions:
                confirmed_ids = set()
                for s in confirmed_sessions:
                    confirmed_ids.add(s.tracking_id)
                    confirmed_ids.update(getattr(s, "stitched_track_ids", []))
                filtered = [tid for tid in track_ids if tid in confirmed_ids]
                if filtered:
                    track_ids = filtered

        for track_id in track_ids:
            events = tracker.get_events_for_track(track_id)
            stats = tracker.get_track_stats(track_id)

            session_duration = 0.0
            if session_manager:
                session = session_manager.get_session(track_id)
                if session and session.end_time is not None and session.start_time is not None:
                    session_duration = max(0.0, session.end_time - session.start_time)

            durations = [
                e.duration_seconds for e in events
                if e.duration_seconds is not None and e.duration_seconds > 0
            ]
            total_attn = sum(durations)
            avg_attn = total_attn / len(durations) if durations else 0.0
            max_attn = max(durations) if durations else 0.0

            target_durations: Dict[str, float] = defaultdict(float)
            for e in events:
                if e.duration_seconds and e.duration_seconds > 0:
                    target_durations[e.target_name] += e.duration_seconds

            most_attended = "—"
            if target_durations:
                most_attended = max(target_durations, key=target_durations.get)

            summaries.append(ShopperAttentionSummary(
                tracking_id=track_id,
                session_duration=session_duration,
                attention_event_count=len(events),
                total_estimated_attention_sec=total_attn,
                average_attention_sec=avg_attn,
                longest_attention_sec=max_attn,
                most_attended_target=most_attended,
                unknown_observation_count=stats.get("unknown_count", 0),
                total_observations=stats.get("total_observations", 0),
            ))
        return summaries

    def _write_shopper_summary_json(self, summaries: List[ShopperAttentionSummary]) -> None:
        path = self.reports_dir / "shopper_attention_summary.json"
        data = {
            "generated_at": datetime.now().isoformat(),
            "note": "All attention durations are estimated from head orientation.",
            "total_shoppers": len(summaries),
            "shoppers": [s.to_dict() for s in summaries],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"  → {path.name}: {len(summaries)} shoppers")

    def _compute_target_summaries(
        self, events: List[AttentionEvent], region_manager: AttentionRegionManager,
    ) -> List[TargetAttentionSummary]:
        target_events: Dict[str, List[AttentionEvent]] = defaultdict(list)
        for e in events:
            target_events[e.target_id].append(e)

        summaries = []
        all_target_ids = set(target_events.keys())
        for region in region_manager.get_all_regions():
            all_target_ids.add(region.id)

        for target_id in sorted(all_target_ids):
            evts = target_events.get(target_id, [])
            region = region_manager.get_region(target_id)
            target_name = region.name if region else target_id
            target_type = region.type if region else "unknown"
            unique_shoppers = len(set(e.tracking_id for e in evts))
            durations = [
                e.duration_seconds for e in evts
                if e.duration_seconds is not None and e.duration_seconds > 0
            ]
            total_dur = sum(durations)
            avg_dur = total_dur / len(durations) if durations else 0.0
            max_dur = max(durations) if durations else 0.0

            summaries.append(TargetAttentionSummary(
                target_id=target_id,
                target_name=target_name,
                target_type=target_type,
                unique_shoppers=unique_shoppers,
                attention_event_count=len(evts),
                total_attention_sec=total_dur,
                average_attention_sec=avg_dur,
                maximum_attention_sec=max_dur,
            ))
        return summaries

    def _write_target_summary_json(self, summaries: List[TargetAttentionSummary]) -> None:
        path = self.reports_dir / "target_attention_summary.json"
        data = {
            "generated_at": datetime.now().isoformat(),
            "note": "All attention values are estimated from head orientation.",
            "total_targets": len(summaries),
            "targets": [s.to_dict() for s in summaries],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"  → {path.name}: {len(summaries)} targets")

    def _write_markdown_report(
        self, stats: dict, events: List[AttentionEvent],
        shopper_summaries: List[ShopperAttentionSummary],
        target_summaries: List[TargetAttentionSummary],
    ) -> None:
        path = self.reports_dir / "attention_report.md"
        durations = [
            e.duration_seconds for e in events
            if e.duration_seconds is not None and e.duration_seconds > 0
        ]
        total_attn = sum(durations)
        avg_attn = total_attn / len(durations) if durations else 0.0

        lines = [
            "# Attention Analysis Report (Module 3 — Phase 5)",
            "",
            "> **Note:** All attention values in this report are *estimated* based on",
            "> head orientation (yaw/pitch/roll). They do NOT represent pixel-level",
            "> eye gaze tracking.",
            "",
            "## Video Information",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Source | {stats.get('video_filename', 'N/A')} |",
            f"| Resolution | {stats.get('video_resolution', 'N/A')} |",
            f"| Duration | {stats.get('video_duration_sec', 0):.1f} sec |",
            f"| Frames Processed | {stats.get('total_frames_processed', 0):,} |",
            f"| Processing Speed | {stats.get('processing_fps', 0):.1f} FPS |",
            f"| Device | {stats.get('device', 'N/A')} |",
            "",
            "## Attention Summary",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Unique Shoppers | {stats.get('total_unique_shoppers', 0)} |",
            f"| Total Attention Events | {len(events)} |",
            f"| Total Est. Attention Time | {total_attn:.1f} sec |",
            f"| Average Attention Duration | {avg_attn:.2f} sec |",
            f"| Detection Method | Head Orientation (MediaPipe + solvePnP) |",
            "",
        ]

        if target_summaries:
            lines.append("## Target Attention Summary")
            lines.append("")
            lines.append(
                "| Target | Type | Shoppers | Events | Total (s) | Avg (s) | Max (s) |"
            )
            lines.append("|---|---|---|---|---|---|---|")
            for ts in target_summaries:
                lines.append(
                    f"| {ts.target_name} | {ts.target_type} | "
                    f"{ts.unique_shoppers} | {ts.attention_event_count} | "
                    f"{ts.total_attention_sec:.1f} | {ts.average_attention_sec:.2f} | "
                    f"{ts.maximum_attention_sec:.2f} |"
                )
            lines.append("")

        if shopper_summaries:
            lines.append("## Shopper Attention Summary")
            lines.append("")
            lines.append(
                "| ID | Events | Total (s) | Avg (s) | Longest (s) | Most Attended | Unknown |"
            )
            lines.append("|---|---|---|---|---|---|---|")
            for ss in shopper_summaries:
                lines.append(
                    f"| {ss.tracking_id} | {ss.attention_event_count} | "
                    f"{ss.total_estimated_attention_sec:.1f} | "
                    f"{ss.average_attention_sec:.2f} | {ss.longest_attention_sec:.2f} | "
                    f"{ss.most_attended_target} | {ss.unknown_observation_count} |"
                )
            lines.append("")

        direction_counts: Dict[str, int] = defaultdict(int)
        for e in events:
            direction_counts[e.attention_direction] += 1
        if direction_counts:
            lines.append("## Attention Direction Distribution")
            lines.append("")
            lines.append("| Direction | Count |")
            lines.append("|---|---|")
            for d, c in sorted(direction_counts.items()):
                lines.append(f"| {d} | {c} |")
            lines.append("")

        lines.append("---")
        lines.append(f"*Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.logger.info(f"  → {path.name}")
