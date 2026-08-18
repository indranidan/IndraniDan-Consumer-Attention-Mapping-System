"""
Dwell-Time Analysis — Report Generator
=========================================
Generates structured output files for Phase 4 dwell-time analytics:
  - dwell_events.json          — all dwell events
  - zone_dwell_summary.json    — per-zone aggregation
  - shopper_dwell_summary.json — per-shopper aggregation
  - dwell_distribution.json    — bucket distribution
  - dwell_time_report.md       — comprehensive Markdown report
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.logger import setup_logger
from ai.dwell_time_analysis.dwell_tracker import DwellTracker
from ai.dwell_time_analysis.dwell_aggregator import (
    DwellAggregator,
    DwellDistribution,
    ShopperDwellSummary,
    ZoneDwellSummary,
)
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_manager import ZoneManager
from ai.utils import ensure_directory


class DwellReportGenerator:
    """Generates all Phase 4 dwell-time report files."""

    def __init__(self, reports_dir: Path, logger: Optional[logging.Logger] = None):
        self.reports_dir = ensure_directory(reports_dir)
        self.logger = logger or setup_logger("dwell_report")

    def generate(
        self,
        processing_stats: Dict,
        dwell_tracker: DwellTracker,
        zone_summaries: List[ZoneDwellSummary],
        shopper_summaries: List[ShopperDwellSummary],
        distribution: DwellDistribution,
        session_manager: SessionManager,
    ) -> Tuple[Path, Path, Path, Path, Path]:
        """
        Generate all Phase 4 report files.

        Returns
        -------
        Tuple of Paths
            (dwell_events.json, zone_dwell_summary.json,
             shopper_dwell_summary.json, dwell_distribution.json,
             dwell_time_report.md)
        """
        self.logger.info("Generating dwell-time analysis reports...")

        # Dwell events JSON
        all_events = dwell_tracker.get_all_events()
        events_path = self._write_json(
            "dwell_events.json",
            {
                "generated_at": datetime.now().isoformat(),
                "total_events": len(all_events),
                "completed_events": sum(1 for e in all_events if e.status == "completed"),
                "track_lost_events": sum(1 for e in all_events if e.status == "track_lost"),
                "events": [e.to_dict() for e in sorted(all_events, key=lambda x: (x.tracking_id, x.entry_time))],
            },
        )

        # Zone dwell summary JSON
        zone_path = self._write_json(
            "zone_dwell_summary.json",
            {
                "generated_at": datetime.now().isoformat(),
                "total_zones": len(zone_summaries),
                "zone_summaries": [s.to_dict() for s in zone_summaries],
            },
        )

        # Shopper dwell summary JSON
        shopper_path = self._write_json(
            "shopper_dwell_summary.json",
            {
                "generated_at": datetime.now().isoformat(),
                "total_shoppers": len(shopper_summaries),
                "shopper_summaries": [s.to_dict() for s in shopper_summaries],
            },
        )

        # Distribution JSON
        dist_path = self._write_json(
            "dwell_distribution.json",
            {
                "generated_at": datetime.now().isoformat(),
                **distribution.to_dict(),
            },
        )

        # Markdown report
        md_path = self._write_markdown_report(
            processing_stats, zone_summaries, shopper_summaries,
            distribution, dwell_tracker, session_manager,
        )

        self.logger.info(f"Dwell events report      : {events_path}")
        self.logger.info(f"Zone dwell summary       : {zone_path}")
        self.logger.info(f"Shopper dwell summary    : {shopper_path}")
        self.logger.info(f"Dwell distribution       : {dist_path}")
        self.logger.info(f"Dwell-time report        : {md_path}")

        return events_path, zone_path, shopper_path, dist_path, md_path

    def _write_json(self, filename: str, data: dict) -> Path:
        """Write data to a JSON file."""
        path = self.reports_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def _write_markdown_report(
        self,
        stats: Dict,
        zone_summaries: List[ZoneDwellSummary],
        shopper_summaries: List[ShopperDwellSummary],
        distribution: DwellDistribution,
        dwell_tracker: DwellTracker,
        session_manager: SessionManager,
    ) -> Path:
        """Generate comprehensive Markdown dwell-time report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Video info
        duration = stats.get("video_duration_sec", 0)
        mins = int(duration // 60)
        secs = duration % 60
        dur_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"

        # Total dwell stats
        all_events = dwell_tracker.get_all_events()
        all_dwell = [
            e.dwell_seconds for e in all_events
            if e.dwell_seconds is not None and e.dwell_seconds >= 0
        ]
        total_dwell = sum(all_dwell) if all_dwell else 0.0
        avg_dwell = total_dwell / len(all_dwell) if all_dwell else 0.0
        median_dwell = 0.0
        if all_dwell:
            import statistics as _stats
            median_dwell = _stats.median(all_dwell)
        max_dwell = max(all_dwell) if all_dwell else 0.0

        # Find longest zone visit
        longest_event = None
        if all_events:
            events_with_dwell = [e for e in all_events if e.dwell_seconds is not None]
            if events_with_dwell:
                longest_event = max(events_with_dwell, key=lambda e: e.dwell_seconds)

        completed_count = sum(1 for e in all_events if e.status == "completed")
        track_lost_count = sum(1 for e in all_events if e.status == "track_lost")

        # Zone-wise table
        zone_rows = ""
        for zs in zone_summaries:
            zone_rows += (
                f"| {zs.zone_id} | {zs.zone_name} | {zs.unique_shoppers} | "
                f"{zs.total_visits} | {zs.completed_visits} | "
                f"{zs.total_dwell_seconds:.1f}s | {zs.average_dwell_seconds:.1f}s | "
                f"{zs.median_dwell_seconds:.1f}s | {zs.min_dwell_seconds:.1f}s | "
                f"{zs.max_dwell_seconds:.1f}s |\n"
            )
        if not zone_rows:
            zone_rows = "| — | — | — | — | — | — | — | — | — | — |\n"

        # Shopper-wise table
        shopper_rows = ""
        for ss in shopper_summaries:
            dur = f"{ss.session_duration:.1f}s" if ss.session_duration is not None else "—"
            shopper_rows += (
                f"| {ss.tracking_id} | {dur} | {ss.session_status} | "
                f"{ss.zones_visited} | {ss.total_zone_visits} | "
                f"{ss.total_observed_dwell_seconds:.1f}s | "
                f"{ss.average_zone_dwell_seconds:.1f}s | "
                f"{ss.longest_zone_visit_seconds:.1f}s | "
                f"{ss.zone_name_with_longest_dwell or '—'} |\n"
            )
        if not shopper_rows:
            shopper_rows = "| — | — | — | — | — | — | — | — | — |\n"

        # Distribution table
        dist_rows = ""
        for bucket in distribution.buckets:
            dist_rows += f"| {bucket.label} | {bucket.visit_count} |\n"
        if not dist_rows:
            dist_rows = "| — | — |\n"

        # ByteTrack config
        mc = stats.get("movement_config", {})

        md = f"""# Dwell-Time Analysis Report

> **Module 3 — Phase 4: Dwell-Time Analytics**
>
> Generated: {timestamp}

---

## 1. Video Information

| Property | Value |
|---|---|
| Input Video | `{stats.get('video_filename', 'N/A')}` |
| Resolution | {stats.get('video_resolution', 'N/A')} |
| Duration | {dur_str} ({duration}s) |
| FPS | {stats.get('video_fps', 'N/A')} |
| Total Frames | {stats.get('total_frames_processed', 0):,} |

---

## 2. Processing Information

| Metric | Value |
|---|---|
| Processing FPS | **{stats.get('processing_fps', 0):.2f}** |
| Avg YOLO Inference | {stats.get('average_yolo_inference_ms', 0):.2f} ms |
| Avg Tracking Time | {stats.get('average_tracking_ms', 0):.2f} ms |
| Total Pipeline Time | {stats.get('total_pipeline_time_sec', 0):.2f}s |
| Device | `{stats.get('device', 'N/A')}` |
| YOLOv8 Model | `{stats.get('model', 'N/A')}` |
| Tracker | `ByteTrack` |
| Track Buffer | {stats.get('track_buffer', 'N/A')} |
| Gap Tolerance | {stats.get('gap_tolerance', 'N/A')} frames |

---

## 3. Dwell-Time Summary

| Metric | Value |
|---|---|
| **Total Unique Shoppers** | **{stats.get('total_unique_shoppers', 0)}** |
| **Total Zone Visits** | **{len(all_events)}** |
| **Total Dwell Time** | **{total_dwell:.1f}s** |
| Average Dwell Time | {avg_dwell:.2f}s |
| Median Dwell Time | {median_dwell:.2f}s |
| Longest Zone Visit | {max_dwell:.1f}s{f' (Person {longest_event.tracking_id} in {longest_event.zone_name})' if longest_event else ''} |
| Completed Visits | {completed_count} |
| Track-Lost Visits | {track_lost_count} |

---

## 4. Zone-wise Dwell Statistics

| Zone ID | Zone Name | Unique Shoppers | Total Visits | Completed | Total Dwell | Avg Dwell | Median | Min | Max |
|---|---|---|---|---|---|---|---|---|---|
{zone_rows}
---

## 5. Shopper-wise Dwell Statistics

| Shopper ID | Session Duration | Status | Zones Visited | Total Visits | Total Dwell | Avg Dwell | Longest Visit | Longest Zone |
|---|---|---|---|---|---|---|---|---|
{shopper_rows}
---

## 6. Dwell-Time Distribution

| Bucket | Visit Count |
|---|---|
{dist_rows}
---

## 7. Artifacts Generated

| File | Path |
|---|---|
| Annotated Video | `{stats.get('output_video', 'N/A')}` |
| Dwell Events JSON | `{self.reports_dir / 'dwell_events.json'}` |
| Zone Dwell Summary | `{self.reports_dir / 'zone_dwell_summary.json'}` |
| Shopper Dwell Summary | `{self.reports_dir / 'shopper_dwell_summary.json'}` |
| Dwell Distribution | `{self.reports_dir / 'dwell_distribution.json'}` |

---

*Report generated by Indrani Consumer Attention Mapping System — Module 3 Phase 4 AI Pipeline*
"""

        md_path = self.reports_dir / "dwell_time_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        return md_path
