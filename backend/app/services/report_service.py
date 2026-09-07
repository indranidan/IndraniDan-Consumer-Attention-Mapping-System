"""
Report Service
==============
Coordinates retail intelligence domain aggregation, server-side document rendering
(PDF, Excel, CSV, JSON), local disk artifact storage, and report ledger persistence.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import get_settings
from app.models.report import ReportRecord
from app.models.store import Store
from app.modules.reports.aggregators import (
    REPORT_TEMPLATES,
    RetailIntelligenceAggregator,
)
from app.modules.reports.pdf_generator import ReportPDFGenerator
from app.modules.reports.excel_generator import ReportExcelGenerator
from app.modules.reports.csv_generator import ReportCSVGenerator
from app.schemas.report import (
    ReportGenerateRequest,
    ReportPreviewRequest,
    ReportPreviewResponse,
    ReportRecordOut,
    ReportTemplateOut,
)


def _format_size(num_bytes: int) -> str:
    """Format bytes into readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


class ReportService:
    """Service handling report lifecycle from compilation to binary delivery."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.pdf_gen = ReportPDFGenerator()
        self.excel_gen = ReportExcelGenerator()
        self.csv_gen = ReportCSVGenerator()

    def get_templates(self) -> List[ReportTemplateOut]:
        """Return available domain report templates."""
        return [ReportTemplateOut(**t) for t in REPORT_TEMPLATES]

    def preview_report(self, db: Session, req: ReportPreviewRequest) -> ReportPreviewResponse:
        """Compile fast aggregated JSON payload for interactive UI preview."""
        aggregator = RetailIntelligenceAggregator(db)
        data = aggregator.compile_report(
            report_type=req.report_type,
            store_id=req.store_id,
            zone_id=req.zone_id,
            date_from=req.date_from,
            date_to=req.date_to,
        )
        return ReportPreviewResponse(
            report_type=data["report_type"],
            title=data["title"],
            store_id=data.get("store_id"),
            store_name=data.get("store_name", "Fleetwide"),
            date_range_label=data.get("date_range_label", "Recent"),
            generated_at=data.get("generated_at", datetime.now(timezone.utc)),
            summary_kpis=data.get("summary_kpis", {}),
            chart_data=data.get("chart_data", {}),
            table_headers=data.get("table_headers", []),
            table_rows=data.get("table_rows", []),
            insights=data.get("insights", []),
        )

    def generate_report(
        self,
        db: Session,
        req: ReportGenerateRequest,
        user_id: Optional[uuid.UUID] = None,
    ) -> ReportRecordOut:
        """Compile report, render requested format to disk, and persist ledger record."""
        aggregator = RetailIntelligenceAggregator(db)
        report_data = aggregator.compile_report(
            report_type=req.report_type,
            store_id=req.store_id,
            zone_id=req.zone_id,
            date_from=req.date_from,
            date_to=req.date_to,
        )

        title = req.title or report_data["title"]
        report_data["title"] = title
        fmt = req.format.lower().strip()
        if fmt not in ["pdf", "excel", "csv", "json"]:
            fmt = "pdf"

        report_id = uuid.uuid4()
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ext = "xlsx" if fmt == "excel" else fmt
        filename = f"{req.report_type}_{timestamp_str}_{report_id.hex[:6]}.{ext}"

        storage_root = Path(self.settings.REPORTS_OUTPUT_PATH)
        storage_root.mkdir(parents=True, exist_ok=True)
        file_path = storage_root / filename

        # Render format
        if fmt == "pdf":
            self.pdf_gen.generate_pdf(report_data, file_path)
        elif fmt == "excel":
            self.excel_gen.generate_excel(report_data, file_path)
        elif fmt == "csv":
            self.csv_gen.generate_csv(report_data, file_path)
        elif fmt == "json":
            file_path.write_text(json.dumps(report_data, default=str, indent=2), encoding="utf-8")

        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Create record in DB
        record = ReportRecord(
            id=report_id,
            title=title,
            report_type=req.report_type,
            format=fmt,
            store_id=report_data.get("store_id"),
            zone_id=req.zone_id,
            date_from=req.date_from,
            date_to=req.date_to,
            file_path=str(file_path),
            file_size=file_size,
            status="ready",
            parameters=req.model_dump(mode="json"),
            summary_kpis=report_data.get("summary_kpis"),
            created_by=user_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return self._to_record_out(record, report_data.get("store_name"))

    def list_reports(
        self,
        db: Session,
        store_id: Optional[uuid.UUID] = None,
        report_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[ReportRecordOut]]:
        """List historical reports from the ledger."""
        query = db.query(ReportRecord)
        if store_id:
            query = query.filter(ReportRecord.store_id == store_id)
        if report_type:
            query = query.filter(ReportRecord.report_type == report_type)

        total = query.count()
        records = query.order_by(desc(ReportRecord.created_at)).offset(skip).limit(limit).all()

        # Cache store names
        store_ids = list(set([r.store_id for r in records if r.store_id]))
        store_map = {}
        if store_ids:
            stores = db.query(Store).filter(Store.id.in_(store_ids)).all()
            store_map = {s.id: s.name for s in stores}

        result = [
            self._to_record_out(r, store_map.get(r.store_id, "Fleetwide"))
            for r in records
        ]
        return total, result

    def get_report(self, db: Session, report_id: uuid.UUID) -> Optional[ReportRecord]:
        """Fetch report by UUID."""
        return db.query(ReportRecord).filter(ReportRecord.id == report_id).first()

    def delete_report(self, db: Session, report_id: uuid.UUID) -> bool:
        """Delete report artifact and DB entry."""
        record = self.get_report(db, report_id)
        if not record:
            return False

        if record.file_path:
            p = Path(record.file_path)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

        db.delete(record)
        db.commit()
        return True

    def _to_record_out(self, record: ReportRecord, store_name: Optional[str] = None) -> ReportRecordOut:
        return ReportRecordOut(
            id=record.id,
            title=record.title,
            report_type=record.report_type,
            format=record.format,
            store_id=record.store_id,
            store_name=store_name or "Fleetwide",
            date_from=record.date_from,
            date_to=record.date_to,
            file_size=record.file_size,
            file_size_formatted=_format_size(record.file_size),
            status=record.status,
            summary_kpis=record.summary_kpis,
            download_url=f"/api/reports/{record.id}/download",
            created_at=record.created_at or datetime.now(timezone.utc),
        )


report_service = ReportService()
