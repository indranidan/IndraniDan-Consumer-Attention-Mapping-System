"""
Report Schemas
==============
Pydantic schemas for the Module 12 Reports & Export System:
- Report template catalogs
- Live preview request/response
- File generation requests
- Report ledger records
"""

import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Report Templates ──────────────────────────────────────────

class ReportTemplateOut(BaseModel):
    """Catalog entry describing a domain report template."""

    report_type: str
    title: str
    description: str
    category: str
    recommended_role: str
    supported_formats: List[str] = ["pdf", "excel", "csv", "json"]
    icon: str


# ── Live Preview ──────────────────────────────────────────────

class ReportPreviewRequest(BaseModel):
    """Parameters to preview aggregated analytics without file compilation."""

    report_type: str = Field(
        ...,
        description="consumer_attention | product_engagement | shelf_performance | conversion_analysis | marketing_effectiveness",
    )
    store_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ReportPreviewResponse(BaseModel):
    """Aggregated analytical payload for instant UI rendering."""

    report_type: str
    title: str
    store_id: Optional[uuid.UUID] = None
    store_name: str
    date_range_label: str
    generated_at: datetime
    summary_kpis: dict[str, Any]
    chart_data: dict[str, Any]
    table_headers: List[dict[str, str]]
    table_rows: List[dict[str, Any]]
    insights: List[str] = []


# ── File Generation ───────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    """Request payload to generate a persistent report artifact."""

    report_type: str = Field(
        ...,
        description="consumer_attention | product_engagement | shelf_performance | conversion_analysis | marketing_effectiveness",
    )
    format: str = Field(
        default="pdf",
        description="pdf | excel | csv | json",
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional custom title for the dossier",
    )
    store_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ── Ledger / Output Schemas ───────────────────────────────────

class ReportRecordOut(BaseModel):
    """Metadata response for a generated report in the ledger."""

    id: uuid.UUID
    title: str
    report_type: str
    format: str
    store_id: Optional[uuid.UUID] = None
    store_name: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    file_size: int = 0
    file_size_formatted: str = "0 KB"
    status: str = "ready"
    summary_kpis: Optional[dict[str, Any]] = None
    download_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportLedgerResponse(BaseModel):
    """Paginated list of historical reports."""

    total: int
    reports: List[ReportRecordOut]
