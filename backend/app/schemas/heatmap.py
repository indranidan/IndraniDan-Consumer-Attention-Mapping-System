"""
Module 7 — Heatmap Schemas
============================
Pydantic response models for the Heatmap Generation Engine API endpoints.
"""

from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


# ── Density Grid Schemas ──────────────────────────────────────

class DensityCell(BaseModel):
    """A single cell in a sparse density grid."""
    x: int
    y: int
    intensity: float = Field(ge=0.0, le=1.0)


class DensityGrid(BaseModel):
    """Sparse 2D density grid for frontend canvas rendering."""
    grid_width: int
    grid_height: int
    max_intensity: float = 0.0
    total_cells: int = 0
    cells: List[DensityCell] = []


class HeatmapMetadata(BaseModel):
    """Metadata about the heatmap computation."""
    grid_width: int = 200
    grid_height: int = 150
    total_input_points: int = 0
    sigma: float = 8.0
    colormap: str = "JET"
    intensity_threshold: float = 0.0


class StoreHeatmapResponse(BaseModel):
    """Response for store-wide attention heatmap."""
    store_id: str
    store_name: str = ""
    grid: DensityGrid
    metadata: HeatmapMetadata
    image_url: Optional[str] = None
    total_cameras: int = 0
    total_jobs_aggregated: int = 0


# ── Shelf Vertical Tier Schemas ───────────────────────────────

class ShelfTierMetric(BaseModel):
    """Metric for a single shelf vertical tier."""
    tier: str
    label: str
    percentage: float = 0.0
    engagement_score: float = 0.0
    gaze_events: int = 0
    total_duration: float = 0.0


class HorizontalBin(BaseModel):
    """A single horizontal bin in shelf width analysis."""
    bin_index: int
    start_pct: float
    end_pct: float
    gaze_events: int = 0
    total_weight: float = 0.0
    percentage: float = 0.0
    normalized_intensity: float = 0.0


class ShelfHeatmapResponse(BaseModel):
    """Response for shelf-level vertical & horizontal heatmap analysis."""
    shelf_id: str
    shelf_name: str = ""
    eye_level_concentration: float = 0.0
    dominant_tier: str = "UNKNOWN"
    vertical_distribution: List[ShelfTierMetric] = []
    horizontal_bins: List[HorizontalBin] = []
    total_gaze_events: int = 0
    total_weight: float = 0.0
    peak_horizontal_bin: Optional[int] = None


# ── Traffic Flow Schemas ──────────────────────────────────────

class FlowVector(BaseModel):
    """A directional flow vector at a grid position."""
    x: int
    y: int
    dx: float
    dy: float
    speed: float = 0.0


class TrafficFlowSummary(BaseModel):
    """Summary statistics for customer traffic flow."""
    total_paths: int = 0
    avg_speed: float = 0.0
    avg_path_length: float = 0.0
    dominant_direction: str = "UNKNOWN"
    direction_counts: Dict[str, int] = {}


class TrafficHeatmapResponse(BaseModel):
    """Response for store traffic flow density."""
    store_id: str
    store_name: str = ""
    grid: DensityGrid
    flow_vectors: List[FlowVector] = []
    summary: TrafficFlowSummary = TrafficFlowSummary()
    metadata: HeatmapMetadata = HeatmapMetadata()


# ── Hotspot Diagnostic Schemas ────────────────────────────────

class DiagnosticZone(BaseModel):
    """A classified retail diagnostic zone."""
    row: int
    col: int
    center_x: float
    center_y: float
    zone_type: str  # HOTSPOT, CONVERSION_ZONE, TRANSIT_CORRIDOR, DEAD_ZONE
    description: str = ""
    severity: str = "MEDIUM"
    recommendation: str = ""
    dwell_to_transit_ratio: float = 0.0
    attention_weight: float = 0.0
    traffic_weight: float = 0.0
    interaction_count: int = 0


class HotspotSummary(BaseModel):
    """Summary of hotspot diagnostic analysis."""
    total_diagnostic_zones: int = 0
    hotspot_count: int = 0
    conversion_zone_count: int = 0
    transit_corridor_count: int = 0
    dead_zone_count: int = 0
    avg_dwell_to_transit_ratio: float = 0.0


class HotspotDiagnosticsResponse(BaseModel):
    """Response for store hotspot and dead-zone diagnostics."""
    store_id: str
    store_name: str = ""
    zones: List[DiagnosticZone] = []
    summary: HotspotSummary = HotspotSummary()
    grid_cols: int = 10
    grid_rows: int = 8


# ── Job-Level Heatmap Schemas ─────────────────────────────────

class JobHeatmapResponse(BaseModel):
    """Combined heatmap response for a single AI job."""
    job_id: str
    store_id: str = ""
    camera_id: str = ""
    grid: DensityGrid = DensityGrid(grid_width=200, grid_height=150)
    shelf_heatmaps: List[ShelfHeatmapResponse] = []
    hotspot_diagnostics: Optional[HotspotDiagnosticsResponse] = None
    traffic: Optional[TrafficHeatmapResponse] = None
    image_url: Optional[str] = None
    metadata: HeatmapMetadata = HeatmapMetadata()
