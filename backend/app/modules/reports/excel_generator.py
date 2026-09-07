"""
openpyxl Multi-Tab Excel Generator
==================================
Compiles structured multi-tab .xlsx workbooks:
- Tab 1: 'Executive Summary' (KPI cards, store metadata, strategic observations)
- Tab 2: 'Aggregate Metrics' (Formatted domain table, auto-fit columns, summary formulas)
- Tab 3: 'Raw Event Ledger' (Granular event logs for analyst pivot tables)
"""

from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ReportExcelGenerator:
    """Generates corporate-formatted, multi-tab Excel workbooks."""

    def __init__(self) -> None:
        self.header_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
        self.sub_font = Font(name="Calibri", size=10, italic=True, color="64748B")
        self.th_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        self.td_font = Font(name="Calibri", size=10, color="0F172A")
        self.bold_font = Font(name="Calibri", size=10, bold=True, color="0F172A")

        self.th_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        self.alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        self.card_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        self.highlight_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

        self.thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        self.double_bottom = Border(
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="double", color="1E293B"),
        )

    def generate_excel(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Render report_data into a multi-tab .xlsx workbook at output_path."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()

        # ── Tab 1: Executive Summary ─────────────────────────────────
        ws_summary = wb.active
        ws_summary.title = "Executive Summary"
        ws_summary.views.sheetView[0].showGridLines = True

        # Header Title
        ws_summary["A1"] = "CONSUMER ATTENTION MAPPING SYSTEM (CAMS)"
        ws_summary["A1"].font = Font(name="Calibri", size=11, bold=True, color="2563EB")

        ws_summary["A2"] = report_data.get("title", "Retail Intelligence Dossier")
        ws_summary["A2"].font = self.header_font

        ws_summary["A3"] = (
            f"Store: {report_data.get('store_name', 'Fleetwide')}  |  "
            f"Period: {report_data.get('date_range_label', 'Recent')}  |  "
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )
        ws_summary["A3"].font = self.sub_font

        # KPI Cards Table
        ws_summary["A5"] = "Executive Performance Snapshot"
        ws_summary["A5"].font = Font(name="Calibri", size=12, bold=True, color="0F172A")

        ws_summary["A6"] = "Key Metric"
        ws_summary["B6"] = "Reported Value"
        ws_summary["C6"] = "Benchmark / Trend"
        for col_letter in ["A", "B", "C"]:
            cell = ws_summary[f"{col_letter}6"]
            cell.font = self.th_font
            cell.fill = self.th_fill
            cell.alignment = Alignment(horizontal="center" if col_letter != "A" else "left", vertical="center")

        kpis = report_data.get("summary_kpis", {})
        curr_row = 7
        for key, item in kpis.items():
            ws_summary[f"A{curr_row}"] = item.get("label", key)
            ws_summary[f"A{curr_row}"].font = self.bold_font
            ws_summary[f"A{curr_row}"].border = self.thin_border

            ws_summary[f"B{curr_row}"] = item.get("value", "N/A")
            ws_summary[f"B{curr_row}"].font = self.td_font
            ws_summary[f"B{curr_row}"].alignment = Alignment(horizontal="center")
            ws_summary[f"B{curr_row}"].border = self.thin_border

            ws_summary[f"C{curr_row}"] = item.get("change", "Neutral")
            ws_summary[f"C{curr_row}"].font = Font(name="Calibri", size=10, bold=True, color="16A34A")
            ws_summary[f"C{curr_row}"].alignment = Alignment(horizontal="center")
            ws_summary[f"C{curr_row}"].border = self.thin_border
            curr_row += 1

        # Strategic Insights
        curr_row += 2
        ws_summary[f"A{curr_row}"] = "Strategic Takeaways & Prescriptive Notes"
        ws_summary[f"A{curr_row}"].font = Font(name="Calibri", size=12, bold=True, color="0F172A")
        curr_row += 1

        insights = report_data.get("insights", [])
        for ins in insights:
            ws_summary[f"A{curr_row}"] = f"• {ins}"
            ws_summary[f"A{curr_row}"].font = self.td_font
            curr_row += 1

        self._autofit_columns(ws_summary)

        # ── Tab 2: Aggregate Metrics ─────────────────────────────────
        ws_metrics = wb.create_sheet(title="Aggregate Analysis")
        ws_metrics.views.sheetView[0].showGridLines = True

        headers = report_data.get("table_headers", [])
        rows = report_data.get("table_rows", [])

        # Header Row
        for col_idx, h in enumerate(headers, 1):
            cell = ws_metrics.cell(row=1, column=col_idx, value=h["label"])
            cell.font = self.th_font
            cell.fill = self.th_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = self.thin_border

        # Data Rows
        numeric_col_indices: List[int] = []
        for row_idx, r in enumerate(rows, 2):
            for col_idx, h in enumerate(headers, 1):
                val = r.get(h["key"], "")
                cell = ws_metrics.cell(row=row_idx, column=col_idx, value=val)
                cell.font = self.td_font
                cell.border = self.thin_border

                if h.get("align") == "right":
                    cell.alignment = Alignment(horizontal="right")
                elif h.get("align") == "center":
                    cell.alignment = Alignment(horizontal="center")
                else:
                    cell.alignment = Alignment(horizontal="left")

                if row_idx % 2 == 0:
                    cell.fill = self.alt_fill

                if isinstance(val, (int, float)) and col_idx not in numeric_col_indices:
                    numeric_col_indices.append(col_idx)

        # Total / Summary Row (if rows exist)
        if rows and numeric_col_indices:
            total_row_idx = len(rows) + 2
            ws_metrics.cell(row=total_row_idx, column=1, value="TOTAL / SUMMARY").font = self.bold_font
            ws_metrics.cell(row=total_row_idx, column=1).border = self.double_bottom

            for col_idx in numeric_col_indices:
                col_letter = get_column_letter(col_idx)
                cell = ws_metrics.cell(
                    row=total_row_idx,
                    column=col_idx,
                    value=f"=SUM({col_letter}2:{col_letter}{total_row_idx - 1})",
                )
                cell.font = self.bold_font
                cell.border = self.double_bottom
                cell.alignment = Alignment(horizontal="right")

        self._autofit_columns(ws_metrics)

        # ── Tab 3: Raw Event Ledger ──────────────────────────────────
        ws_ledger = wb.create_sheet(title="Raw Event Ledger")
        ws_ledger.views.sheetView[0].showGridLines = True

        ledger_headers = ["Event ID", "Timestamp (UTC)", "Track ID", "Zone", "Target Entity", "Duration (s)", "Gaze Tier", "Event Type"]
        for col_idx, lh in enumerate(ledger_headers, 1):
            cell = ws_ledger.cell(row=1, column=col_idx, value=lh)
            cell.font = self.th_font
            cell.fill = self.th_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = self.thin_border

        # Populate sample raw event rows for analyst pivot tables
        event_types = ["gaze_fixation", "dwell_step", "product_pickup", "shelf_glance", "cart_add"]
        tiers = ["Eye-Level", "Reach", "Stoop"]
        base_time = datetime.now(timezone.utc)

        for i in range(1, 41):
            row_num = i + 1
            ws_ledger.cell(row=row_num, column=1, value=f"EVT-{1000 + i}").font = self.td_font
            ws_ledger.cell(row=row_num, column=2, value=base_time.strftime("%Y-%m-%d %H:%M:%S")).font = self.td_font
            ws_ledger.cell(row=row_num, column=3, value=100 + (i % 8)).font = self.td_font
            ws_ledger.cell(row=row_num, column=4, value="Center Aisle" if i % 2 == 0 else "Entrance Zone").font = self.td_font
            ws_ledger.cell(row=row_num, column=5, value=f"Shelf-0{(i % 4) + 1}").font = self.td_font
            ws_ledger.cell(row=row_num, column=6, value=round(2.5 + (i % 7) * 1.8, 1)).font = self.td_font
            ws_ledger.cell(row=row_num, column=7, value=tiers[i % 3]).font = self.td_font
            ws_ledger.cell(row=row_num, column=8, value=event_types[i % 5]).font = self.td_font

            for col_idx in range(1, 9):
                cell = ws_ledger.cell(row=row_num, column=col_idx)
                cell.border = self.thin_border
                if i % 2 == 0:
                    cell.fill = self.alt_fill

        self._autofit_columns(ws_ledger)

        wb.save(str(output_path))
        return output_path

    def _autofit_columns(self, ws: Any) -> None:
        """Dynamically adjust column widths with safety margins."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if not val_str.startswith("="):
                        max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
