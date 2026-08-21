"""
Module 5 — Product Interaction Report Generator
================================================
Generates structured JSON and Markdown reports for Module 5:
- Product Interaction Summary
- Product Engagement Matrix
- Shelf Interaction Monitoring
- Granular Interaction Events Log
- Observed Multi-Product Comparisons & Consideration Journeys
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.module5.models import (
    Module5Summary,
    ProductComparisonPattern,
    ProductEngagementMetric,
    ProductInteractionEvent,
    ShelfInteractionMetric,
)


class Module5ReportGenerator:
    """Generates JSON and Markdown reports for Module 5."""

    def generate_json_report(
        self,
        summary: Module5Summary,
        products: List[ProductEngagementMetric],
        shelves: List[ShelfInteractionMetric],
        events: List[ProductInteractionEvent],
        comparisons: List[ProductComparisonPattern],
        job_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compile complete structured dictionary for JSON export."""
        return {
            "module": "Module 5 — Product Interaction Analysis Module",
            "report_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "job_metadata": job_metadata or {},
            "summary": summary.to_dict(),
            "products": [p.to_dict() for p in products],
            "shelves": [s.to_dict() for s in shelves],
            "comparisons": [c.to_dict() for c in comparisons],
            "events_sample": [e.to_dict() for e in events[:500]],
            "total_event_count": len(events),
            "disclaimer": summary.disclaimer,
        }

    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Render a clean GitHub-flavored Markdown report."""
        summary = report_data.get("summary", {})
        products = report_data.get("products", [])
        shelves = report_data.get("shelves", [])
        comparisons = report_data.get("comparisons", [])
        events = report_data.get("events_sample", [])
        meta = report_data.get("job_metadata", {})

        md: List[str] = [
            "# Module 5 — Product Interaction Analysis Report",
            "",
            f"**Generated:** {report_data.get('generated_at', datetime.now(timezone.utc).isoformat())}  ",
            f"**Store ID:** `{meta.get('store_id', 'N/A')}` | **Camera ID:** `{meta.get('camera_id', 'N/A')}`",
            "",
            "---",
            "",
            "## 1. Product Interaction Summary",
            "",
            "| Metric | Value | Status / Note |",
            "|:---|:---|:---|",
            f"| **Total Product Views** | {summary.get('total_views', 0)} | Deduplicated viewing events |",
            f"| **Unique Product Viewers** | {summary.get('total_unique_viewers', 0)} | Unique ByteTrack shoppers |",
            f"| **Total View Duration** | {summary.get('total_view_duration_sec', 0.0):.2f}s | Cumulative attention duration |",
            f"| **Average View Duration** | {summary.get('average_view_duration_sec', 0.0):.2f}s | Mean duration per view event |",
            f"| **Total Pickups** | {summary.get('total_pickups', 0)} | {summary.get('pickup_detection_status', 'N/A')} |",
            f"| **Total Returns** | {summary.get('total_returns', 0)} | Verified prior-pickup returns |",
            f"| **Observed Comparisons** | {summary.get('total_comparisons', 0)} | Multi-product consideration patterns |",
            f"| **Product Purchases** | {summary.get('total_purchases', 0)} | {summary.get('purchase_data_status', 'N/A')} |",
            f"| **Shelf Interactions** | {summary.get('total_shelf_interactions', 0)} | Sustained shopper interactions |",
            "",
            "> [!NOTE]",
            f"> {summary.get('disclaimer', '')}",
            "",
            "---",
            "",
            "## 2. Product Engagement Metrics",
            "",
        ]

        if products:
            md.extend([
                "| Product Name | SKU | Shelf | Views | Unique Viewers | Total View Duration | Avg Duration | Pickups | Returns | Comparisons | Repeat Views | Status |",
                "|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|",
            ])
            for p in products:
                md.append(
                    f"| **{p.get('product_name', 'Unknown')}** | `{p.get('sku') or 'N/A'}` | {p.get('shelf_name') or 'N/A'} "
                    f"| {p.get('views', 0)} | {p.get('unique_viewers', 0)} | {p.get('total_view_duration_sec', 0.0):.2f}s "
                    f"| {p.get('average_view_duration_sec', 0.0):.2f}s | {p.get('pickup_events', 0)} | {p.get('return_events', 0)} "
                    f"| {p.get('comparison_events', 0)} | {p.get('repeat_interactions', 0)} | {p.get('status_note', 'Active')} |"
                )
        else:
            md.append("*No individual products configured for this store/camera.*")

        md.extend([
            "",
            "---",
            "",
            "## 3. Shelf Interaction Monitoring",
            "",
            "| Shelf Name | Shelf Code | Shelf Visits | Shelf Viewers | Attention Events | Attention Duration | Product Views | Shelf Interactions | Pickups | Returns | Engagement Time |",
            "|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|",
        ])

        if shelves:
            for s in shelves:
                md.append(
                    f"| **{s.get('shelf_name', 'Unknown')}** | `{s.get('shelf_code') or s.get('shelf_id')}` "
                    f"| {s.get('shelf_visits', 0)} | {s.get('shelf_viewers', 0)} | {s.get('shelf_attention_events', 0)} "
                    f"| {s.get('shelf_attention_duration_sec', 0.0):.2f}s | {s.get('product_views', 0)} "
                    f"| {s.get('shelf_interactions', 0)} | {s.get('pickup_events', 0)} | {s.get('return_events', 0)} "
                    f"| {s.get('total_engagement_duration_sec', 0.0):.2f}s |"
                )
        else:
            md.append("*No shelves configured for this store/camera.*")

        md.extend([
            "",
            "---",
            "",
            "## 4. Multi-Product Comparison & Consideration Patterns",
            "",
        ])

        if comparisons:
            for c in comparisons:
                md.extend([
                    f"### Pattern `{c.get('pattern_id')}` — Track ID #{c.get('track_id')} (Session `{c.get('session_id') or 'N/A'}`)",
                    f"- **Description:** {c.get('pattern_description')}",
                    f"- **Total Duration:** {c.get('total_duration_sec', 0.0):.2f}s (from {c.get('start_time', 0.0):.2f}s to {c.get('end_time', 0.0):.2f}s)",
                    f"- **Items Compared:** {', '.join(c.get('product_names', []))}",
                    "",
                    "**Sequence Steps:**",
                ])
                for step in c.get("interaction_sequence", []):
                    md.append(
                        f"  - `{step.get('start_time')}s - {step.get('end_time')}s`: **{step.get('product_name')}** ({step.get('event_type')}, duration: {step.get('duration_seconds')}s)"
                    )
                md.append("")
        else:
            md.append("*No multi-product comparison sequences observed in this session.*")

        md.extend([
            "",
            "---",
            "",
            "## 5. Granular Interaction Events Log",
            "",
            "| Event ID | Event Type | Track ID | Product | Shelf | Start Time | End Time | Duration | Confidence | Source |",
            "|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|",
        ])

        if events:
            for ev in events[:50]:
                md.append(
                    f"| `{ev.get('event_id')}` | **{ev.get('event_type')}** | #{ev.get('track_id')} "
                    f"| {ev.get('product_name') or 'N/A'} | {ev.get('shelf_name') or 'N/A'} "
                    f"| {ev.get('start_time', 0.0):.2f}s | {ev.get('end_time', 0.0):.2f}s "
                    f"| {ev.get('duration_seconds', 0.0):.2f}s | {ev.get('confidence', 0.0):.2f} "
                    f"| `{ev.get('source')}` |"
                )
            if len(events) > 50:
                md.append(f"\n*Showing 50 of {len(events)} events. Full log available in JSON export.*")
        else:
            md.append("*No interaction events recorded.*")

        return "\n".join(md)

    def write_reports(self, report_data: Dict[str, Any], output_dir: Path) -> Tuple[Path, Path]:
        """Write both JSON and Markdown reports to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "module5_interaction_report.json"
        md_path = output_dir / "module5_interaction_report.md"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        md_content = self.generate_markdown_report(report_data)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_path, md_path
