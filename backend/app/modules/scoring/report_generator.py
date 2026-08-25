"""
Module 8 — Product Attractiveness Scoring Report Generator
===========================================================
Generates structured JSON and Markdown intelligence reports for Module 8:
- Product Attractiveness Leaderboard
- Five-Pillar Score Breakdown
- Shelf Visibility & Tier Analysis
- Confidence & Sample Size Report
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.modules.scoring.models import (
    Module8Summary,
    ProductScoreProfile,
)


class Module8ReportGenerator:
    """Generates JSON and Markdown reports for Module 8 scoring."""

    def generate_json_report(
        self,
        summary: Module8Summary,
        products: List[ProductScoreProfile],
        job_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compile complete structured dictionary for JSON export."""
        sorted_products = sorted(
            products, key=lambda p: p.attractiveness_score, reverse=True
        )
        return {
            "module": "Module 8 — Product Attractiveness Scoring Engine",
            "report_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "job_metadata": job_metadata or {},
            "summary": summary.to_dict(),
            "products": [p.to_dict() for p in sorted_products],
            "total_products_scored": len(products),
            "disclaimer": summary.disclaimer,
        }

    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Render a clean GitHub-flavored Markdown report."""
        summary = report_data.get("summary", {})
        products = report_data.get("products", [])
        meta = report_data.get("job_metadata", {})

        md: List[str] = [
            "# Module 8 — Product Attractiveness Scoring Report",
            "",
            f"**Generated:** {report_data.get('generated_at', datetime.now(timezone.utc).isoformat())}  ",
            f"**Store ID:** `{meta.get('store_id', 'N/A')}` | **Camera ID:** `{meta.get('camera_id', 'N/A')}`",
            "",
            "---",
            "",
            "## 1. Scoring Summary",
            "",
            "| Metric | Value |",
            "|:---|:---|",
            f"| **Products Scored** | {summary.get('total_products_scored', 0)} |",
            f"| **Average Attractiveness** | {summary.get('average_attractiveness_score', 0.0):.1f} / 100 |",
            f"| **Top Performer** | {summary.get('top_performer_name', 'N/A')} ({summary.get('top_performer_score', 0.0):.1f}) |",
            f"| **Bottom Performer** | {summary.get('bottom_performer_name', 'N/A')} ({summary.get('bottom_performer_score', 0.0):.1f}) |",
            f"| **Average Confidence** | {summary.get('average_confidence', 0.0):.2%} |",
            "",
        ]

        # Leaderboard table
        if products:
            md.extend([
                "---",
                "",
                "## 2. Product Attractiveness Leaderboard",
                "",
                "| Rank | Product | SKU | Score | Rating | Confidence | Intrinsic |",
                "|:---:|:---|:---|:---:|:---:|:---:|:---:|",
            ])
            for rank, p in enumerate(products, 1):
                pillar = p.get("pillar_scores", {})
                conf = p.get("confidence", {})
                md.append(
                    f"| {rank} "
                    f"| {p.get('product_name', 'Unknown')} "
                    f"| `{p.get('sku', 'N/A')}` "
                    f"| **{p.get('attractiveness_score', 0.0):.1f}** "
                    f"| {pillar.get('rating', 'D')} "
                    f"| {conf.get('confidence_level', 'Low')} ({conf.get('sample_size', 0)}) "
                    f"| {p.get('intrinsic_attractiveness_score', 0.0):.1f} |"
                )
            md.append("")

        # Five-Pillar Breakdown
        if products:
            md.extend([
                "---",
                "",
                "## 3. Five-Pillar Score Breakdown",
                "",
                "| Product | Attention | Interaction | Pickup | Conversion | Repeat |",
                "|:---|:---:|:---:|:---:|:---:|:---:|",
            ])
            for p in products:
                pillar = p.get("pillar_scores", {})
                md.append(
                    f"| {p.get('product_name', 'Unknown')} "
                    f"| {pillar.get('attention_score', 0.0):.3f} "
                    f"| {pillar.get('interaction_score', 0.0):.3f} "
                    f"| {pillar.get('pickup_score', 0.0):.3f} "
                    f"| {pillar.get('conversion_score', 0.0):.3f} "
                    f"| {pillar.get('repeat_score', 0.0):.3f} |"
                )
            md.append("")

        # Shelf Visibility Matrix
        if products:
            md.extend([
                "---",
                "",
                "## 4. Shelf Visibility & Tier Analysis",
                "",
                "| Product | Shelf | Tier | γ Coefficient | Visibility Score | Observed → Intrinsic |",
                "|:---|:---|:---:|:---:|:---:|:---|",
            ])
            for p in products:
                sv = p.get("shelf_visibility", {})
                obs = p.get("attractiveness_score", 0.0)
                intrinsic = p.get("intrinsic_attractiveness_score", 0.0)
                md.append(
                    f"| {p.get('product_name', 'Unknown')} "
                    f"| {sv.get('shelf_name', 'N/A')} "
                    f"| {sv.get('shelf_tier', 'UNKNOWN')} "
                    f"| {sv.get('gamma_coefficient', 0.75):.2f} "
                    f"| {sv.get('visibility_score', 0.0):.1f} "
                    f"| {obs:.1f} → {intrinsic:.1f} |"
                )
            md.append("")

        # Disclaimer
        md.extend([
            "---",
            "",
            f"> {summary.get('disclaimer', '')}",
            "",
        ])

        return "\n".join(md)

    def save_reports(
        self,
        report_data: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Path]:
        """Save JSON and Markdown reports to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "module8_scoring_report.json"
        json_path.write_text(
            json.dumps(report_data, indent=2, default=str),
            encoding="utf-8",
        )

        md_text = self.generate_markdown_report(report_data)
        md_path = output_dir / "module8_scoring_report.md"
        md_path.write_text(md_text, encoding="utf-8")

        return {"json": json_path, "markdown": md_path}
