"""
Module 12 — Reports & Export System Tests
==========================================
Comprehensive tests for:
- Domain aggregators across all 5 analytical retail domains
- PDF vector generation (ReportLab)
- Multi-tab Excel workbook compilation (openpyxl)
- Flat CSV generation
- ReportService lifecycle & ledger persistence
- REST API endpoint contracts
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import openpyxl
import pytest

from app.modules.reports.aggregators import (
    REPORT_TEMPLATES,
    RetailIntelligenceAggregator,
)
from app.modules.reports.pdf_generator import ReportPDFGenerator
from app.modules.reports.excel_generator import ReportExcelGenerator
from app.modules.reports.csv_generator import ReportCSVGenerator
from app.services.report_service import ReportService
from app.schemas.report import ReportPreviewRequest, ReportGenerateRequest


@pytest.fixture
def mock_db():
    """Mock database session with empty/default queries."""
    db = MagicMock()
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = None
    query_mock.limit.return_value = query_mock
    query_mock.count.return_value = 0
    query_mock.order_by.return_value = query_mock
    query_mock.offset.return_value = query_mock
    db.query.return_value = query_mock
    return db


# ── 1. Domain Aggregator Tests ────────────────────────────────

class TestReportAggregators:
    """Verifies each of the 5 retail intelligence domain aggregators."""

    def test_templates_catalog(self):
        """All 5 mandated report templates exist in catalog."""
        types = [t["report_type"] for t in REPORT_TEMPLATES]
        assert "consumer_attention" in types
        assert "product_engagement" in types
        assert "shelf_performance" in types
        assert "conversion_analysis" in types
        assert "marketing_effectiveness" in types
        assert len(types) == 5

    def test_consumer_attention_aggregation(self, mock_db):
        """Consumer attention aggregator produces KPIs and table headers."""
        aggregator = RetailIntelligenceAggregator(mock_db)
        data = aggregator.compile_report("consumer_attention")

        assert data["report_type"] == "consumer_attention"
        assert "summary_kpis" in data
        assert "avg_dwell" in data["summary_kpis"]
        assert "eye_level_share" in data["summary_kpis"]
        assert len(data["table_headers"]) >= 5
        assert len(data["table_rows"]) >= 1
        assert len(data["insights"]) >= 1

    def test_product_engagement_aggregation(self, mock_db):
        """Product engagement aggregator computes view-to-pickup ratios."""
        aggregator = RetailIntelligenceAggregator(mock_db)
        data = aggregator.compile_report("product_engagement")

        assert data["report_type"] == "product_engagement"
        assert "pickup_rate" in data["summary_kpis"]
        assert "total_pickups" in data["summary_kpis"]
        assert any(h["key"] == "pickup_rate" for h in data["table_headers"])

    def test_shelf_performance_aggregation(self, mock_db):
        """Shelf performance aggregator identifies tiers and dead zones."""
        aggregator = RetailIntelligenceAggregator(mock_db)
        data = aggregator.compile_report("shelf_performance")

        assert data["report_type"] == "shelf_performance"
        assert "eye_yield" in data["summary_kpis"]
        assert "dead_zone_count" in data["summary_kpis"]

    def test_conversion_analysis_aggregation(self, mock_db):
        """Conversion analysis aggregator computes 5-pillar scores."""
        aggregator = RetailIntelligenceAggregator(mock_db)
        data = aggregator.compile_report("conversion_analysis")

        assert data["report_type"] == "conversion_analysis"
        assert "avg_attractiveness" in data["summary_kpis"]
        assert any(h["key"] == "attention_pillar" for h in data["table_headers"])

    def test_marketing_effectiveness_aggregation(self, mock_db):
        """Marketing aggregator computes promotional lift and ROI multiplier."""
        aggregator = RetailIntelligenceAggregator(mock_db)
        data = aggregator.compile_report("marketing_effectiveness")

        assert data["report_type"] == "marketing_effectiveness"
        assert "campaign_lift" in data["summary_kpis"]
        assert "roi_index" in data["summary_kpis"]

    def test_invalid_report_type_raises(self, mock_db):
        """Unknown report type raises ValueError."""
        aggregator = RetailIntelligenceAggregator(mock_db)
        with pytest.raises(ValueError, match="Unknown report type"):
            aggregator.compile_report("non_existent_type")


# ── 2. Document Generator Tests ───────────────────────────────

class TestDocumentGenerators:
    """Verifies file generation for PDF, Excel, and CSV engines."""

    @pytest.fixture
    def sample_report_data(self, mock_db):
        aggregator = RetailIntelligenceAggregator(mock_db)
        return aggregator.compile_report("consumer_attention")

    def test_pdf_generation(self, sample_report_data, tmp_path):
        """ReportPDFGenerator compiles a valid vector PDF file."""
        pdf_path = tmp_path / "test_report.pdf"
        generator = ReportPDFGenerator()
        out = generator.generate_pdf(sample_report_data, pdf_path)

        assert out.exists()
        assert out.stat().st_size > 500  # Non-empty file
        with open(out, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"

    def test_excel_generation(self, sample_report_data, tmp_path):
        """ReportExcelGenerator compiles a multi-tab .xlsx workbook."""
        xlsx_path = tmp_path / "test_report.xlsx"
        generator = ReportExcelGenerator()
        out = generator.generate_excel(sample_report_data, xlsx_path)

        assert out.exists()
        assert out.stat().st_size > 500

        # Verify workbook structure
        wb = openpyxl.load_workbook(str(out))
        sheet_names = wb.sheetnames
        assert "Executive Summary" in sheet_names
        assert "Aggregate Analysis" in sheet_names
        assert "Raw Event Ledger" in sheet_names

    def test_csv_generation(self, sample_report_data, tmp_path):
        """ReportCSVGenerator outputs structured CSV format."""
        csv_path = tmp_path / "test_report.csv"
        generator = ReportCSVGenerator()
        out = generator.generate_csv(sample_report_data, csv_path)

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "CAMS RETAIL INTELLIGENCE REPORT" in content
        assert "EXECUTIVE SUMMARY KPIS" in content


# ── 3. Report Service Lifecycle Tests ─────────────────────────

class TestReportService:
    """Tests service layer coordination."""

    def test_get_templates(self):
        svc = ReportService()
        templates = svc.get_templates()
        assert len(templates) == 5
        assert all(hasattr(t, "title") for t in templates)

    def test_preview_report(self, mock_db):
        svc = ReportService()
        req = ReportPreviewRequest(report_type="product_engagement")
        preview = svc.preview_report(mock_db, req)
        assert preview.report_type == "product_engagement"
        assert preview.summary_kpis is not None
        assert len(preview.table_rows) > 0

    def test_generate_report_pdf(self, mock_db, tmp_path):
        svc = ReportService()
        svc.settings.REPORTS_OUTPUT_PATH = str(tmp_path)

        req = ReportGenerateRequest(
            report_type="shelf_performance",
            format="pdf",
        )
        record = svc.generate_report(mock_db, req, user_id=uuid.uuid4())

        assert record.report_type == "shelf_performance"
        assert record.format == "pdf"
        assert record.file_size > 0
        assert mock_db.add.called
        assert mock_db.commit.called
