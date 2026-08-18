"""
Person Tracking — Report Generator
====================================
Generates comprehensive session reports for multi-person tracking in:
- outputs/module3/phase2/reports/tracking_report.json
- outputs/module3/phase2/reports/tracking_report.md
- outputs/module3/phase2/reports/tracks.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.logger import setup_logger
from ai.person_tracking.tracker import TrackInfo
from ai.utils import ensure_directory


class TrackingReportGenerator:
    """Generates structured tracking reports in JSON and Markdown formats."""

    def __init__(self, reports_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Initialize report generator.

        Parameters
        ----------
        reports_dir : Path
            Target directory for report artifacts.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.reports_dir = ensure_directory(reports_dir)
        self.logger = logger or setup_logger("tracking_report_generator")

    def generate(
        self,
        session_stats: Dict,
        track_history: Dict[int, TrackInfo],
        frame_tracking_records: List[Dict],
    ) -> Tuple[Path, Path, Path]:
        """
        Generate tracking_report.json, tracking_report.md, and tracks.json.

        Parameters
        ----------
        session_stats : Dict
            Session-level summary statistics from TrackingVideoProcessor.
        track_history : Dict[int, TrackInfo]
            Master map of track_id to TrackInfo.
        frame_tracking_records : List[Dict]
            Per-frame tracking records.

        Returns
        -------
        Tuple[Path, Path, Path]
            Paths to (tracking_report.json, tracking_report.md, tracks.json).
        """
        self.logger.info("Generating tracking session reports...")

        json_report_path = self.generate_json_report(session_stats, track_history)
        md_report_path = self.generate_markdown_report(session_stats, track_history)
        tracks_json_path = self.generate_tracks_json(frame_tracking_records)

        self.logger.info(f"Summary JSON Report    : {json_report_path}")
        self.logger.info(f"Summary Markdown Report: {md_report_path}")
        self.logger.info(f"Frame Tracks JSON      : {tracks_json_path}")

        return json_report_path, md_report_path, tracks_json_path

    def generate_json_report(
        self,
        session_stats: Dict,
        track_history: Dict[int, TrackInfo],
    ) -> Path:
        """Save overall session stats and track details as tracking_report.json."""
        tracks_summary = [
            track_info.to_dict() for track_info in sorted(track_history.values(), key=lambda t: t.track_id)
        ]

        report_data = {
            "report_type": "person_tracking",
            "module": "Module 3 — Phase 2",
            "generated_at": datetime.now().isoformat(),
            **session_stats,
            "tracks_summary": tracks_summary,
        }

        json_path = self.reports_dir / "tracking_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return json_path

    def generate_markdown_report(
        self,
        session_stats: Dict,
        track_history: Dict[int, TrackInfo],
    ) -> Path:
        """Save readable summary report as tracking_report.md."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        duration = session_stats.get("video_duration_sec", 0)
        mins = int(duration // 60)
        secs = duration % 60
        duration_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"

        # Build Markdown table for tracked IDs
        tracks_table_rows = []
        sorted_tracks = sorted(track_history.values(), key=lambda t: t.track_id)

        for t in sorted_tracks:
            row = (
                f"| `{t.track_id}` | {t.first_frame} | {t.last_frame} | "
                f"{t.frames_tracked} | {t.first_timestamp:.2f}s | {t.last_timestamp:.2f}s | "
                f"{t.average_confidence:.4f} |"
            )
            tracks_table_rows.append(row)

        tracks_table_content = (
            "\n".join(tracks_table_rows)
            if tracks_table_rows
            else "| - | - | - | - | - | - | - |"
        )

        md_content = f"""# Multi-Person Tracking Report (ByteTrack)

> **Module 3 — Phase 2: Multi-Person Tracking**
>
> Generated: {timestamp}

---

## Executive Summary

| Property | Value |
|---|---|
| Input Video | `{session_stats.get('video_filename', 'N/A')}` |
| Video Resolution | {session_stats.get('video_resolution', 'N/A')} |
| Video Duration | {duration_str} ({session_stats.get('video_duration_sec', 0)}s) |
| Video FPS | {session_stats.get('video_fps', 'N/A')} |
| Total Frames Processed | {session_stats.get('total_frames_processed', 0):,} |

---

## Tracking Metrics

| Metric | Value |
|---|---|
| **Total Unique Person IDs** | **{session_stats.get('total_unique_tracking_ids', 0)}** |
| Max Simultaneous Tracked People | {session_stats.get('max_simultaneous_tracked_people', 0)} |
| Average Active Tracks per Frame | {session_stats.get('average_active_tracks', 0):.2f} |
| Total Person Detections | {session_stats.get('total_person_detections', 0):,} |
| Average Tracking Confidence | {session_stats.get('average_tracking_confidence', 0):.4f} |

---

## Performance & Execution

| Metric | Value |
|---|---|
| Average YOLO Inference Time | {session_stats.get('average_yolo_inference_time_ms', 0):.2f} ms |
| Average ByteTrack Time | {session_stats.get('average_bytetrack_time_ms', 0):.2f} ms |
| Processing Speed (FPS) | **{session_stats.get('processing_fps', 0):.2f} FPS** |
| Execution Device | `{session_stats.get('device', 'N/A')}` |
| YOLO Model | `{session_stats.get('model', 'N/A')}` |
| Tracking Algorithm | `{session_stats.get('tracker', 'ByteTrack')}` |

---

## Tracker Configuration

| Setting | Value |
|---|---|
| Track High Threshold | {session_stats.get('track_high_threshold', 'N/A')} |
| Track Low Threshold | {session_stats.get('track_low_threshold', 'N/A')} |
| New Track Threshold | {session_stats.get('new_track_threshold', 'N/A')} |
| Track Buffer (Frames) | {session_stats.get('track_buffer', 'N/A')} |
| Match Threshold (IoU) | {session_stats.get('match_threshold', 'N/A')} |

---

## Tracked Person Details

| Person ID | First Frame | Last Frame | Frames Tracked | First Timestamp | Last Timestamp | Avg Confidence |
|---|---|---|---|---|---|---|
{tracks_table_content}

---

## Artifacts Generated

| Description | File Path |
|---|---|
| Annotated Output Video | `{session_stats.get('output_video', 'N/A')}` |
| Summary JSON Report | `{self.reports_dir / 'tracking_report.json'}` |
| Frame-Level Tracks Data | `{self.reports_dir / 'tracks.json'}` |

---

*Report generated by Indrani Consumer Attention Mapping System — Module 3 Phase 2 AI Pipeline*
"""

        md_path = self.reports_dir / "tracking_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return md_path

    def generate_tracks_json(self, frame_tracking_records: List[Dict]) -> Path:
        """Save frame-by-frame raw track coordinates as tracks.json for downstream analytics."""
        tracks_json_path = self.reports_dir / "tracks.json"

        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_frames": len(frame_tracking_records),
            },
            "frames": frame_tracking_records,
        }

        with open(tracks_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return tracks_json_path
