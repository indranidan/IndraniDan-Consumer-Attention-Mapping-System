"""
Movement Analysis — Report Generator
=======================================
Generates structured output files for Phase 3 movement analysis:
  - sessions.json     — shopper sessions with paths, zones, journeys
  - paths.json        — raw path data per shopper
  - zone_visits.json  — zone visit records
  - traffic_summary.json — traffic statistics
  - movement_report.md — comprehensive Markdown report
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.logger import setup_logger
from ai.movement_analysis.path_tracker import PathTracker
from ai.movement_analysis.session_manager import SessionManager
from ai.movement_analysis.zone_tracker import ZoneTracker
from ai.utils import ensure_directory


class MovementReportGenerator:
    """Generates all Phase 3 report files."""

    def __init__(self, reports_dir: Path, logger: Optional[logging.Logger] = None):
        self.reports_dir = ensure_directory(reports_dir)
        self.logger = logger or setup_logger("movement_report")

    def generate(
        self,
        session_stats: Dict,
        session_manager: SessionManager,
        path_tracker: PathTracker,
        zone_tracker: ZoneTracker,
    ) -> Tuple[Path, Path, Path, Path, Path]:
        """
        Generate all 5 report files.

        Returns
        -------
        Tuple of Paths
            (sessions.json, paths.json, zone_visits.json, traffic_summary.json, movement_report.md)
        """
        self.logger.info("Generating movement analysis reports...")

        sessions_path = self._write_json(
            "sessions.json",
            {"generated_at": datetime.now().isoformat(), "sessions": session_manager.get_all_sessions_dicts()},
        )

        paths_path = self._write_json(
            "paths.json",
            {"generated_at": datetime.now().isoformat(), "paths": path_tracker.get_all_paths_dicts()},
        )

        zone_visits_path = self._write_json(
            "zone_visits.json",
            {"generated_at": datetime.now().isoformat(), "zone_visits": zone_tracker.get_all_zone_visits()},
        )

        traffic_path = self._write_json(
            "traffic_summary.json",
            {"generated_at": datetime.now().isoformat(), **session_stats.get("traffic_stats", {})},
        )

        md_path = self._write_markdown_report(session_stats, session_manager)

        self.logger.info(f"Sessions report     : {sessions_path}")
        self.logger.info(f"Paths report        : {paths_path}")
        self.logger.info(f"Zone visits report  : {zone_visits_path}")
        self.logger.info(f"Traffic summary     : {traffic_path}")
        self.logger.info(f"Movement report     : {md_path}")

        return sessions_path, paths_path, zone_visits_path, traffic_path, md_path

    def _write_json(self, filename: str, data: dict) -> Path:
        path = self.reports_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def _write_markdown_report(self, stats: Dict, session_manager: SessionManager) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        traffic = stats.get("traffic_stats", {})

        duration = stats.get("video_duration_sec", 0)
        mins = int(duration // 60)
        secs = duration % 60
        dur_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"

        # Zone statistics table
        zone_stats = traffic.get("zone_statistics", [])
        zone_rows = ""
        for zs in zone_stats:
            zone_rows += f"| {zs['zone_id']} | {zs['zone_name']} | {zs['unique_visitors']} | {zs['total_visits']} |\n"
        if not zone_rows:
            zone_rows = "| — | — | — | — |\n"

        # Zone transitions table
        transition_matrix = traffic.get("zone_transition_matrix", {})
        transition_rows = ""
        for from_zone, targets in transition_matrix.items():
            for to_zone, count in targets.items():
                transition_rows += f"| {from_zone} | {to_zone} | {count} |\n"
        if not transition_rows:
            transition_rows = "| — | — | — |\n"

        # Session table
        sessions = session_manager.get_all_sessions()
        session_rows = ""
        for s in sessions:
            zones = ", ".join(s.zones_visited) if s.zones_visited else "—"
            entry_t = f"{s.entry_time:.1f}s" if s.entry_time is not None else "—"
            exit_t = f"{s.exit_time:.1f}s" if s.exit_time is not None else "—"
            session_rows += (
                f"| {s.session_id} | {s.tracking_id} | {s.status} | "
                f"{entry_t} | {exit_t} | {s.frames_tracked} | "
                f"{s.average_confidence:.4f} | {zones} |\n"
            )
        if not session_rows:
            session_rows = "| — | — | — | — | — | — | — | — |\n"

        # Per-shopper journey
        journey_sections = ""
        for s in sessions:
            journey_sections += f"\n### Shopper ID {s.tracking_id}\n\n"
            if s.journey:
                for evt in s.journey:
                    loc = evt.get("zone_name", evt.get("location", "—"))
                    journey_sections += f"- **{evt['display_time']}** → {evt['event']}: {loc}\n"
            else:
                journey_sections += "- No journey events recorded.\n"

        md = f"""# Movement Analysis Report

> **Module 3 — Phase 3: Movement Intelligence**
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
| Model | `{stats.get('model', 'N/A')}` |
| Tracker | `{stats.get('tracker', 'ByteTrack')}` |

---

## 3. Traffic Summary

| Metric | Value |
|---|---|
| **Total Unique Shoppers** | **{stats.get('total_unique_shoppers', 0)}** |
| Total Entries | {stats.get('total_entries', 0)} |
| Total Exits | {stats.get('total_exits', 0)} |
| Track Lost | {stats.get('total_track_lost', 0)} |
| Max Simultaneous Shoppers | {stats.get('max_simultaneous_shoppers', 0)} |
| Average Active Shoppers | {stats.get('average_active_shoppers', 0):.2f} |

---

## 4. Zone Statistics

| Zone ID | Zone Name | Unique Visitors | Total Visits |
|---|---|---|---|
{zone_rows}
---

## 5. Zone Transitions

| From Zone | To Zone | Count |
|---|---|---|
{transition_rows}
---

## 6. Shopper Sessions

| Session | Track ID | Status | Entry | Exit | Frames | Avg Conf | Zones Visited |
|---|---|---|---|---|---|---|---|
{session_rows}
---

## 7. Per-Shopper Journey
{journey_sections}
---

## 8. Artifacts Generated

| File | Path |
|---|---|
| Annotated Video | `{stats.get('output_video', 'N/A')}` |
| Sessions JSON | `{self.reports_dir / 'sessions.json'}` |
| Paths JSON | `{self.reports_dir / 'paths.json'}` |
| Zone Visits JSON | `{self.reports_dir / 'zone_visits.json'}` |
| Traffic Summary | `{self.reports_dir / 'traffic_summary.json'}` |

---

*Report generated by Indrani Consumer Attention Mapping System — Module 3 Phase 3 AI Pipeline*
"""

        md_path = self.reports_dir / "movement_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        return md_path
