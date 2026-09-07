"""
Flat CSV Report Generator
=========================
Outputs standardized CSV datasets containing report metadata, executive KPIs,
and tabular domain rows for downstream ETL pipelines.
"""

import csv
from pathlib import Path
from typing import Any, Dict


class ReportCSVGenerator:
    """Generates clean, RFC 4180-compliant CSV reports."""

    def generate_csv(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Export tabular rows and summary KPIs into a structured CSV file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = report_data.get("table_headers", [])
        rows = report_data.get("table_rows", [])
        kpis = report_data.get("summary_kpis", {})

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Metadata Comments / Headers
            writer.writerow(["# CAMS RETAIL INTELLIGENCE REPORT"])
            writer.writerow(["# Title", report_data.get("title", "")])
            writer.writerow(["# Store", report_data.get("store_name", "")])
            writer.writerow(["# Period", report_data.get("date_range_label", "")])
            writer.writerow(["# Generated", str(report_data.get("generated_at", ""))])
            writer.writerow([])

            # Executive Summary Section
            if kpis:
                writer.writerow(["# EXECUTIVE SUMMARY KPIS"])
                writer.writerow(["Metric", "Value", "Trend"])
                for k, item in kpis.items():
                    writer.writerow([item.get("label", k), item.get("value", ""), item.get("change", "")])
                writer.writerow([])

            # Tabular Data Section
            if headers:
                writer.writerow([h["label"] for h in headers])
                for r in rows:
                    writer.writerow([r.get(h["key"], "") for h in headers])

        return output_path
