"""
ReportLab PDF Generation Engine
================================
Compiles professional, vector-styled retail intelligence PDF dossiers with:
- Corporate branding header & title banner
- Multi-column Executive KPI callout grids
- Strategic Takeaways callout box
- Formatted, auto-wrapped tabular breakdowns with zebra striping
- Two-pass NumberedCanvas for 'Page X of Y' footers
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to compute total page count and draw running header/footer."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Any] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running footer line
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 35, letter[0] - 40, 35)

        # Footer text
        footer_left = "CAMS — Consumer Attention Mapping System | Confidential Retail Analytics"
        footer_right = f"Page {self._pageNumber} of {page_count}"
        self.drawString(40, 24, footer_left)
        self.drawRightString(letter[0] - 40, 24, footer_right)

        self.restoreState()


class ReportPDFGenerator:
    """Renders structured report payloads into branded vector PDF files."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self) -> None:
        self.title_style = ParagraphStyle(
            "CAMS_Title",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        self.subtitle_style = ParagraphStyle(
            "CAMS_Subtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        )
        self.meta_label = ParagraphStyle(
            "CAMS_MetaLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0284c7"),
        )
        self.meta_val = ParagraphStyle(
            "CAMS_MetaVal",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        self.section_header = ParagraphStyle(
            "CAMS_SectionHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=12,
            spaceAfter=6,
        )
        self.kpi_value = ParagraphStyle(
            "CAMS_KPIVal",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # Centered
            textColor=colors.HexColor("#0284c7"),
        )
        self.kpi_label = ParagraphStyle(
            "CAMS_KPILabel",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor("#475569"),
        )
        self.kpi_change = ParagraphStyle(
            "CAMS_KPIChange",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=1,
            textColor=colors.HexColor("#16a34a"),
        )
        self.table_header_style = ParagraphStyle(
            "CAMS_TH",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.white,
        )
        self.table_cell_style = ParagraphStyle(
            "CAMS_TD",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        )
        self.insight_bullet = ParagraphStyle(
            "CAMS_Insight",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=4,
        )

    def generate_pdf(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Render report_data dictionary into a vector PDF file at output_path."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=50,
        )

        story: List[Any] = []

        # ── 1. Header Banner & Title ─────────────────────────────────
        brand_heading = Paragraph(
            "CONSUMER ATTENTION MAPPING SYSTEM (CAMS)",
            ParagraphStyle(
                "BrandSub",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=colors.HexColor("#2563eb"),
                spaceAfter=2,
            ),
        )
        story.append(brand_heading)

        title = Paragraph(report_data.get("title", "Retail Intelligence Dossier"), self.title_style)
        story.append(title)

        # ── 2. Metadata Bar ──────────────────────────────────────────
        store_name = report_data.get("store_name", "Fleetwide")
        date_label = report_data.get("date_range_label", "Recent Analysis")
        gen_time = datetime.now(timezone.utc).strftime("%b %d, %Y - %H:%M UTC")

        meta_table_data = [
            [
                Paragraph("<b>STORE / LOCATION</b>", self.meta_label),
                Paragraph("<b>ANALYZED PERIOD</b>", self.meta_label),
                Paragraph("<b>REPORT COMPILED</b>", self.meta_label),
            ],
            [
                Paragraph(store_name, self.meta_val),
                Paragraph(date_label, self.meta_val),
                Paragraph(gen_time, self.meta_val),
            ],
        ]
        meta_table = Table(meta_table_data, colWidths=[200, 180, 150])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # ── 3. Executive KPI Cards ───────────────────────────────────
        kpis = report_data.get("summary_kpis", {})
        if kpis:
            story.append(Paragraph("Executive Performance Snapshot", self.section_header))
            kpi_cols: List[List[Paragraph]] = []
            for k, info in list(kpis.items())[:4]:
                col_content = [
                    Spacer(1, 4),
                    Paragraph(str(info.get("value", "N/A")), self.kpi_value),
                    Paragraph(str(info.get("label", k)), self.kpi_label),
                    Paragraph(f"▲ {info.get('change', 'Neutral')}", self.kpi_change),
                    Spacer(1, 4),
                ]
                kpi_cols.append(col_content)

            # Transpose into 1 row of cells
            col_width = (letter[0] - 80) / max(len(kpi_cols), 1)
            kpi_table = Table([kpi_cols], colWidths=[col_width] * len(kpi_cols))
            kpi_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            story.append(kpi_table)
            story.append(Spacer(1, 14))

        # ── 4. Strategic Insights & Takeaways ────────────────────────
        insights = report_data.get("insights", [])
        if insights:
            story.append(Paragraph("Strategic Takeaways & Prescriptive Insights", self.section_header))
            insight_flowables = [
                Paragraph("<b>KEY OBSERVATIONS & RECOMMENDATIONS</b>", self.meta_label),
                Spacer(1, 4),
            ]
            for ins in insights:
                insight_flowables.append(Paragraph(f"• {ins}", self.insight_bullet))

            insight_table = Table([[insight_flowables]], colWidths=[letter[0] - 80])
            insight_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ])
            )
            story.append(insight_table)
            story.append(Spacer(1, 14))

        # ── 5. Detailed Tabular Breakdown ────────────────────────────
        headers = report_data.get("table_headers", [])
        rows = report_data.get("table_rows", [])
        if headers and rows:
            story.append(Paragraph("Detailed Analytical Breakdown", self.section_header))

            table_content: List[List[Paragraph]] = []
            header_row = [Paragraph(f"<b>{h['label']}</b>", self.table_header_style) for h in headers]
            table_content.append(header_row)

            for r in rows:
                data_row = []
                for h in headers:
                    val = str(r.get(h["key"], "—"))
                    align_style = ParagraphStyle(
                        f"Align_{h['key']}",
                        parent=self.table_cell_style,
                        alignment=1 if h.get("align") == "center" else (2 if h.get("align") == "right" else 0),
                    )
                    data_row.append(Paragraph(val, align_style))
                table_content.append(data_row)

            num_cols = len(headers)
            avail_width = letter[0] - 80
            col_widths = [avail_width / num_cols] * num_cols
            # Give first text column slightly more width if rank column exists
            if num_cols >= 4 and headers[0]["key"] == "rank":
                col_widths[0] = 35
                col_widths[1] = avail_width * 0.30
                remaining = (avail_width - 35 - col_widths[1]) / (num_cols - 2)
                for c in range(2, num_cols):
                    col_widths[c] = remaining

            data_table = Table(table_content, colWidths=col_widths, repeatRows=1)
            table_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
            for row_idx in range(1, len(table_content)):
                if row_idx % 2 == 0:
                    table_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#f8fafc")))
            data_table.setStyle(TableStyle(table_styles))
            story.append(data_table)

        # Build document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return output_path
