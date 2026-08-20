"""
Module 4 — Attention Report Generator
=======================================
Generates comprehensive JSON and Markdown attention analysis reports for Module 4.
All results are clearly documented as estimated head-orientation-based attention.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.module4.models import (
    AttentionEventRecord,
    AttentionQualityMetrics,
    Module4Summary,
    ProductAttention,
    ShelfEngagement,
)


class Module4ReportGenerator:
    """Generates JSON and Markdown reports for Module 4."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir

    def generate_json_report(
        self,
        summary: Module4Summary,
        shelves: List[ShelfEngagement],
        products: List[ProductAttention],
        events: List[AttentionEventRecord],
        quality: Optional[AttentionQualityMetrics] = None,
        job_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON report object."""
        report = {
            "module": "Module 4 — Attention Analysis Engine",
            "report_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "job_metadata": job_metadata or {},
            "summary": summary.to_dict(),
            "shelves": [s.to_dict() for s in shelves],
            "products": [p.to_dict() for p in products],
            "quality_metrics": quality.to_dict() if quality else None,
            "events_sample": [e.to_dict() for e in events[:100]],
            "total_event_count": len(events),
            "disclaimer": (
                "Attention metrics are ESTIMATED based on 3D head pose and orientation "
                "relative to configured regions. Typical retail CCTV cameras do not support "
                "pixel-level pupil tracking. Results represent viewing direction proxies."
            ),
        }
        return report

    def generate_markdown_report(
        self,
        report_data: Dict[str, Any],
    ) -> str:
        """Render a clean GitHub-Flavored Markdown report."""
        summary = report_data.get("summary", {})
        shelves = report_data.get("shelves", [])
        products = report_data.get("products", [])
        quality = report_data.get("quality_metrics", {})
        meta = report_data.get("job_metadata", {})

        lines = [
            "# Module 4 — Consumer Attention Analysis Report",
            "",
            f"*Generated at: {report_data.get('generated_at', '')}*",
            "",
            "> [!NOTE]",
            "> **Estimated Attention Analysis**: All attention durations and target associations",
            "> are estimated from 3D head orientation (yaw/pitch/roll) relative to configured regions.",
            "> They do NOT represent pupil-level eye gaze or psychological purchase intent.",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| **Total Attention Events** | {summary.get('total_attention_events', 0)} |",
            f"| **Total Attention Duration** | {summary.get('total_attention_duration_sec', 0.0):.2f}s |",
            f"| **Average Event Duration** | {summary.get('average_attention_duration_sec', 0.0):.2f}s |",
            f"| **Total Dwell Time** | {summary.get('total_dwell_time_sec', 0.0):.2f}s |",
            f"| **Total Shelf Attention Time** | {summary.get('total_shelf_attention_time_sec', 0.0):.2f}s |",
            f"| **Repeated Attention Events** | {summary.get('total_repeated_attention_events', 0)} |",
            f"| **Unique Viewers** | {summary.get('total_unique_viewers', 0)} |",
            f"| **Average Shelf Engagement Score** | {summary.get('shelf_engagement_score_avg', 0.0):.1f} / 100 |",
            "",
            "## 2. Shelf Engagement Analysis",
            "",
            "| Shelf Name | Visitors | Viewers | Dwell Time | Attention Time | Avg Attention | Repeated Visits | Engagement Score |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        if shelves:
            for s in shelves:
                lines.append(
                    f"| **{s.get('shelf_name', '—')}** | {s.get('visitors', 0)} | "
                    f"{s.get('viewers', 0)} | {s.get('dwell_time_sec', 0.0):.1f}s | "
                    f"{s.get('shelf_attention_time_sec', 0.0):.1f}s | "
                    f"{s.get('average_shelf_attention_sec', 0.0):.2f}s | "
                    f"{s.get('repeated_attention_events', 0)} | "
                    f"**{s.get('score', 0.0):.1f}** |"
                )
        else:
            lines.append("| *No shelf regions configured* | — | — | — | — | — | — | — |")

        lines.extend([
            "",
            "## 3. Product Attention Analysis",
            "",
        ])

        if summary.get("product_mapping_configured") and products:
            lines.extend([
                "| Product Name | SKU | Viewers | Attention Events | Focus Duration | Avg Focus | Repeated Focus |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for p in products:
                lines.append(
                    f"| **{p.get('product_name', '—')}** | {p.get('sku', '—')} | "
                    f"{p.get('viewers', 0)} | {p.get('attention_events', 0)} | "
                    f"{p.get('total_focus_duration_sec', 0.0):.1f}s | "
                    f"{p.get('average_focus_duration_sec', 0.0):.2f}s | "
                    f"{p.get('repeated_attention_events', 0)} |"
                )
        else:
            lines.extend([
                "> [!WARNING]",
                "> **Product Spatial Mapping Not Configured**: Pixel coordinates / bounding polygons",
                "> for individual products have not been configured for this camera. Product-level focus",
                "> metrics remain marked as *Unavailable / Not Configured*. Shelf-level attention is active.",
                "",
            ])

        if quality:
            lines.extend([
                "## 4. Detection Quality & Pose Confidence",
                "",
                "| Quality Metric | Value |",
                "| :--- | :--- |",
                f"| **Total Frames Analyzed** | {quality.get('total_frames_analyzed', 0)} |",
                f"| **Valid Face Detections** | {quality.get('valid_face_detections', 0)} |",
                f"| **Low Confidence / Occluded** | {quality.get('low_confidence_faces', 0) + quality.get('occluded_or_missing_faces', 0)} |",
                f"| **Face Detection Rate** | {quality.get('face_detection_rate', 0.0) * 100:.1f}% |",
                f"| **Average Pose Confidence** | {quality.get('average_pose_confidence', 0.0):.2f} |",
                "",
            ])

        lines.extend([
            "## 5. Technical Limitations & Explainability",
            "",
            "1. **Head Pose vs Eye Gaze**: MediaPipe FaceLandmarker detects 6 3D facial landmarks and solvePnP computes Euler angles. This models head orientation, serving as an effective approximation in overhead camera views.",
            "2. **Physical Dwell vs Attention**: A shopper standing inside a zone without looking at a shelf is credited with Zone Dwell Time, but NOT Shelf Attention Time.",
            "3. **Score Methodology**: The Shelf Engagement Score is an analytical synthesis of attention-to-dwell ratio (40%), total attention duration (35%), and repeated visits (25%).",
            "",
        ])

        return "\n".join(lines)

    def write_reports(
        self,
        report_data: Dict[str, Any],
        output_dir: Path,
    ) -> Tuple[Path, Path]:
        """Save JSON and MD reports to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "module4_attention_report.json"
        md_path = output_dir / "module4_attention_report.md"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        md_content = self.generate_markdown_report(report_data)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_path, md_path
