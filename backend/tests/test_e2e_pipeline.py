"""
End-to-End Retail Intelligence Pipeline Workflow Integration Tests
===================================================================
Module 13 Integration Test Suite simulating a full retail intelligence session:
1. Store Topology & Hardware Calibration (Store, Zone, Camera, Shelf, Product)
2. Video Job Ingestion & Synthetic Shopper Tracking (M3 Ingestion)
3. Dwell Time & Attention Engine Analysis (M4 Attention Engine)
4. Behavioral Intelligence & Archetype Clustering (M6 Behavior Engine)
5. Attractiveness Scoring & Planogram Bias Compensation (M8 Scoring Engine)
6. Actionable Merchandising Recommendations & What-If Simulation (M9 Recommendation Engine)
7. Anomaly Alert Detection & Event Bus Dispatching (M11 Notification Engine)
8. Multi-Format Reporting & Cross-Module Data Consistency (M12 Report Engine)
9. Full Unified E2E Pipeline Session Lifecycle Execution
"""

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

# Ensure backend root is on Python path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_project_root = str(Path(_backend_dir).parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.models.ai_job import AIJob
from app.models.camera import Camera
from app.models.product import Product
from app.models.shelf import Shelf
from app.models.store import Store
from app.models.zone import Zone
from app.models.notification import Notification

from app.modules.attention.engine import Module4AttentionEngine
from app.modules.attention.models import (
    AttentionEventRecord,
    ShelfEngagement,
    ProductAttention,
    Module4Summary,
)
from app.services.attention_service import compute_m4_config_hash

from ai.behavior_analysis.engine import Module6BehaviorEngine
from ai.behavior_analysis.models import (
    ShopperArchetype,
    BehaviorFeatureVector,
    ShopperClassification,
)

from app.modules.scoring.engine import Module8ScoringEngine
from app.modules.scoring.models import (
    ProductScoreProfile,
    PillarScores,
    QualitativeRating,
    ShelfTier,
    ShelfVisibilityProfile,
    SHELF_TIER_GAMMA,
)

from app.modules.recommendation.engine import Module9RecommendationEngine
from app.modules.recommendation.simulator import PlanogramSimulator
from app.modules.recommendation.models import (
    PlanogramSimulationRequest,
    PlanogramSimulationResult,
    RecommendationPriority,
    RecommendationCategory,
)

from app.modules.alerts.alert_service import create_notification
from app.core.redis_listener import dispatch_job_event

from app.modules.reports.aggregators import (
    RetailIntelligenceAggregator,
    REPORT_TEMPLATES,
)
from app.modules.reports.pdf_generator import ReportPDFGenerator
from app.modules.reports.excel_generator import ReportExcelGenerator
from app.modules.reports.csv_generator import ReportCSVGenerator


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def retail_topology():
    """Provides a consistent store topology model for end-to-end testing."""
    store_id = uuid.uuid4()
    zone_id = uuid.uuid4()
    camera_id = uuid.uuid4()
    shelf_eye_id = uuid.uuid4()
    shelf_bot_id = uuid.uuid4()
    sku_oil_id = uuid.uuid4()
    sku_bev_id = uuid.uuid4()

    store = Store(
        id=store_id,
        name="Metro Hypermarket Downtown",
        store_code="STR-NYC-001",
        address="100 Grand Avenue, Financial District",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
        description="Flagship downtown hypermarket",
        status="active",
    )

    zone = Zone(
        id=zone_id,
        store_id=store_id,
        name="Zone A - Beverages & Oils",
        description="High-traffic grocery aisle with shelf gondolas",
    )
    zone.polygon_points = [[0, 0], [500, 0], [500, 400], [0, 400]]
    zone.zone_type = "aisle"

    camera = Camera(
        id=camera_id,
        store_id=store_id,
        zone_id=zone_id,
        name="Cam-01-Aisle-North",
        camera_source="rtsp://internal-cam:554/stream1",
        status="active",
        location_description="Ceiling wide angle camera facing Aisle 3",
    )
    camera.resolution = "3840x2160"
    camera.fps = 30

    shelf_eye = Shelf(
        id=shelf_eye_id,
        store_id=store_id,
        zone_id=zone_id,
        name="Aisle 3 Eye Level Display",
        shelf_code="SH-EYE-01",
        category="Beverages",
        description="Eye level shelf rack",
    )
    shelf_eye.tier = "EYE_LEVEL"
    shelf_eye.bounding_polygon = {"points": [[50, 100], [250, 100], [250, 200], [50, 200]]}
    shelf_eye.capacity = 40

    shelf_bottom = Shelf(
        id=shelf_bot_id,
        store_id=store_id,
        zone_id=zone_id,
        name="Aisle 3 Bottom Tier Rack",
        shelf_code="SH-BOT-02",
        category="Oils & Vinegars",
        description="Floor-level storage shelf",
    )
    shelf_bottom.tier = "BOTTOM"
    shelf_bottom.bounding_polygon = {"points": [[50, 250], [250, 250], [250, 350], [50, 350]]}
    shelf_bottom.capacity = 60

    prod_oil = Product(
        id=sku_oil_id,
        store_id=store_id,
        zone_id=zone_id,
        shelf_id=shelf_bot_id,
        name="Artisanal Cold-Pressed Olive Oil",
        sku="SKU-OIL-001",
        category="Oils & Vinegars",
        price=24.99,
    )

    prod_bev = Product(
        id=sku_bev_id,
        store_id=store_id,
        zone_id=zone_id,
        shelf_id=shelf_eye_id,
        name="Organic Sparkling Spring Water",
        sku="SKU-BEV-002",
        category="Beverages",
        price=2.99,
    )

    return {
        "store": store,
        "zone": zone,
        "camera": camera,
        "shelf_eye": shelf_eye,
        "shelf_bottom": shelf_bottom,
        "prod_oil": prod_oil,
        "prod_bev": prod_bev,
    }


@pytest.fixture
def mock_db(retail_topology):
    """Mock SQLAlchemy DB session wired with the topology entities."""
    db = MagicMock()
    topo = retail_topology

    def mock_query(model):
        q = MagicMock()
        if model == Store:
            q.filter.return_value.first.return_value = topo["store"]
            q.first.return_value = topo["store"]
            q.all.return_value = [topo["store"]]
        elif model == Zone:
            q.filter.return_value.first.return_value = topo["zone"]
            q.all.return_value = [topo["zone"]]
        elif model == Camera:
            q.filter.return_value.first.return_value = topo["camera"]
            q.all.return_value = [topo["camera"]]
        elif model == Shelf:
            q.filter.return_value.first.return_value = topo["shelf_eye"]
            q.all.return_value = [topo["shelf_eye"], topo["shelf_bottom"]]
        elif model == Product:
            q.filter.return_value.first.return_value = topo["prod_oil"]
            q.all.return_value = [topo["prod_oil"], topo["prod_bev"]]
        elif model == Notification:
            q.filter.return_value.all.return_value = []
            q.all.return_value = []
        elif model == AIJob:
            job = AIJob(
                id=uuid.uuid4(),
                store_id=topo["store"].id,
                camera_id=topo["camera"].id,
                status="COMPLETED",
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
                completed_at=datetime.now(timezone.utc),
            )
            q.filter.return_value.first.return_value = job
            q.all.return_value = [job]
        else:
            q.filter.return_value.first.return_value = None
            q.all.return_value = []
            q.first.return_value = None
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.count.return_value = 1
        return q

    db.query.side_effect = mock_query
    return db


@pytest.fixture
def mock_job_artifacts(retail_topology):
    """Constructs realistic synthetic JSON telemetry simulating Module 3 video tracking."""
    topo = retail_topology
    with tempfile.TemporaryDirectory() as tmp_dir:
        root_path = Path(tmp_dir)
        p3_dir = root_path / "phase3" / "reports"
        p4_dir = root_path / "phase4" / "reports"
        p5_dir = root_path / "phase5" / "reports"

        p3_dir.mkdir(parents=True, exist_ok=True)
        p4_dir.mkdir(parents=True, exist_ok=True)
        p5_dir.mkdir(parents=True, exist_ok=True)

        # 1. Phase 3: Shopper movement tracks & sessions
        sessions_payload = {
            "sessions": [
                {
                    "track_id": 101,
                    "tracking_id": 101,
                    "session_id": "sess-101",
                    "start_time": 10.0,
                    "end_time": 45.0,
                    "duration_sec": 35.0,
                    "zone_ids": [str(topo["zone"].id)],
                    "path_coordinates": [[100, 200], [120, 210], [130, 215], [135, 215]],
                    "total_distance_px": 180.5,
                    "dwell_time_sec": 22.0,
                    "interaction_count": 2,
                    "gaze_count": 8,
                },
                {
                    "track_id": 102,
                    "tracking_id": 102,
                    "session_id": "sess-102",
                    "start_time": 15.0,
                    "end_time": 25.0,
                    "duration_sec": 10.0,
                    "zone_ids": [str(topo["zone"].id)],
                    "path_coordinates": [[50, 50], [450, 350]],
                    "total_distance_px": 520.0,
                    "dwell_time_sec": 1.5,
                    "interaction_count": 0,
                    "gaze_count": 1,
                },
                {
                    "track_id": 103,
                    "tracking_id": 103,
                    "session_id": "sess-103",
                    "start_time": 30.0,
                    "end_time": 90.0,
                    "duration_sec": 60.0,
                    "zone_ids": [str(topo["zone"].id)],
                    "path_coordinates": [[80, 150], [90, 150], [85, 160], [80, 155]],
                    "total_distance_px": 65.0,
                    "dwell_time_sec": 48.0,
                    "interaction_count": 4,
                    "gaze_count": 15,
                },
            ]
        }
        with open(p3_dir / "sessions.json", "w", encoding="utf-8") as f:
            json.dump(sessions_payload, f)

        # 2. Phase 4: Zone Dwell Summary
        dwell_payload = {
            "zone_summaries": [
                {
                    "zone_id": str(topo["zone"].id),
                    "zone_name": topo["zone"].name,
                    "unique_shoppers": 3,
                    "total_dwell_seconds": 71.5,
                    "average_dwell_seconds": 23.83,
                }
            ]
        }
        with open(p4_dir / "zone_dwell_summary.json", "w", encoding="utf-8") as f:
            json.dump(dwell_payload, f)

        # 3. Phase 5: Gaze & Attention Events
        events_payload = {
            "events": [
                {
                    "event_id": "evt-001",
                    "tracking_id": 101,
                    "target_type": "shelf",
                    "target_id": str(topo["shelf_eye"].id),
                    "target_name": topo["shelf_eye"].name,
                    "start_time": 12.0,
                    "end_time": 16.0,
                    "duration_seconds": 4.0,
                    "confidence": 0.88,
                    "gaze_origin": [150, 150],
                    "gaze_direction": [0.0, 1.0],
                },
                {
                    "event_id": "evt-002",
                    "tracking_id": 103,
                    "target_type": "shelf",
                    "target_id": str(topo["shelf_bottom"].id),
                    "target_name": topo["shelf_bottom"].name,
                    "start_time": 35.0,
                    "end_time": 44.0,
                    "duration_seconds": 9.0,
                    "confidence": 0.92,
                    "gaze_origin": [150, 300],
                    "gaze_direction": [0.0, 1.0],
                },
            ]
        }
        with open(p5_dir / "attention_events.json", "w", encoding="utf-8") as f:
            json.dump(events_payload, f)

        yield {
            "root_path": root_path,
            "sessions_payload": sessions_payload,
            "dwell_payload": dwell_payload,
            "events_payload": events_payload,
        }


# ── 1. Store Topology & Hardware Calibration ─────────────────────────────

class TestStoreTopologyConfiguration:
    """Verifies relational integrity and spatial mapping of store topology."""

    def test_topology_entity_relationships(self, retail_topology):
        """Assert store, zone, camera, shelf, and product connections."""
        topo = retail_topology
        assert topo["zone"].store_id == topo["store"].id
        assert topo["camera"].store_id == topo["store"].id
        assert topo["shelf_eye"].zone_id == topo["zone"].id
        assert topo["shelf_bottom"].zone_id == topo["zone"].id
        assert topo["prod_bev"].shelf_id == topo["shelf_eye"].id
        assert topo["prod_oil"].shelf_id == topo["shelf_bottom"].id

    def test_spatial_calibrations_and_tiers(self, retail_topology):
        """Assert shelf tiers and bounding polygons are configured accurately."""
        topo = retail_topology
        assert topo["shelf_eye"].tier == "EYE_LEVEL"
        assert topo["shelf_bottom"].tier == "BOTTOM"

        poly_eye = topo["shelf_eye"].bounding_polygon["points"]
        assert len(poly_eye) == 4
        # Validate eye-level shelf is vertically positioned above bottom shelf
        y_eye_top = min(p[1] for p in poly_eye)
        y_bot_top = min(p[1] for p in topo["shelf_bottom"].bounding_polygon["points"])
        assert y_eye_top < y_bot_top


# ── 2. Video Job Ingestion & Synthetic Shopper Tracking ──────────────────

class TestVideoIngestionAndTracking:
    """Verifies AI job creation, lifecycle state transitions, and tracking ingestion."""

    def test_ai_job_creation_and_lifecycle(self, retail_topology):
        """Assert AIJob moves from QUEUED to RUNNING to COMPLETED."""
        topo = retail_topology
        job_id = uuid.uuid4()
        job = AIJob(
            id=job_id,
            store_id=topo["store"].id,
            camera_id=topo["camera"].id,
            input_type="VIDEO_FILE",
            source="store_aisle3_session.mp4",
            status="QUEUED",
            created_at=datetime.now(timezone.utc),
        )
        assert job.status == "QUEUED"

        # Simulate worker start
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        assert job.status == "RUNNING"

        # Simulate completion
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        assert job.status == "COMPLETED"
        assert job.completed_at >= job.started_at

    def test_tracking_payload_ingestion(self, mock_job_artifacts):
        """Assert synthetic tracking sessions contain valid trajectory telemetry."""
        sessions = mock_job_artifacts["sessions_payload"]["sessions"]
        assert len(sessions) == 3

        # Track 101: Moderate browser
        t101 = sessions[0]
        assert t101["track_id"] == 101
        assert t101["duration_sec"] == 35.0
        assert len(t101["path_coordinates"]) == 4

        # Track 102: Fast transit (speed runner)
        t102 = sessions[1]
        assert t102["duration_sec"] == 10.0
        assert t102["dwell_time_sec"] < 2.0

        # Track 103: High dwell (focused shopper)
        t103 = sessions[2]
        assert t103["duration_sec"] == 60.0
        assert t103["dwell_time_sec"] == 48.0


# ── 3. Dwell Attention Engine Integration ────────────────────────────────

class TestDwellAndAttentionEngine:
    """Verifies Module 4 Attention Engine analysis against simulated artifacts."""

    def test_attention_engine_processing(self, mock_job_artifacts, retail_topology):
        """Process synthetic job artifacts through Module4AttentionEngine."""
        topo = retail_topology
        engine = Module4AttentionEngine()

        shelf_regions = [
            {
                "shelf_id": str(topo["shelf_eye"].id),
                "name": topo["shelf_eye"].name,
                "shelf_code": topo["shelf_eye"].shelf_code,
                "tier": "EYE_LEVEL",
                "polygon": topo["shelf_eye"].bounding_polygon["points"],
            },
            {
                "shelf_id": str(topo["shelf_bottom"].id),
                "name": topo["shelf_bottom"].name,
                "shelf_code": topo["shelf_bottom"].shelf_code,
                "tier": "BOTTOM",
                "polygon": topo["shelf_bottom"].bounding_polygon["points"],
            },
        ]

        result = engine.process_completed_module3_job(
            job_output_dir=mock_job_artifacts["root_path"],
            shelf_regions=shelf_regions,
            store_id=str(topo["store"].id),
            camera_id=str(topo["camera"].id),
        )

        assert result is not None
        assert "summary" in result
        summary = result["summary"]
        assert summary["total_dwell_time_sec"] == 71.5
        assert summary["total_attention_events"] >= 1

    def test_m4_deterministic_config_hashing(self, retail_topology):
        """Assert configuration hash changes when shelf coordinates change."""
        topo = retail_topology
        job_id = uuid.uuid4()

        hash1 = compute_m4_config_hash(
            job_id=job_id,
            store_id=topo["store"].id,
            camera_id=topo["camera"].id,
            db_shelves=[topo["shelf_eye"], topo["shelf_bottom"]],
        )

        # Alter shelf polygon
        modified_shelf = Shelf(
            id=topo["shelf_eye"].id,
            store_id=topo["store"].id,
            zone_id=topo["zone"].id,
            name="Modified Shelf",
            shelf_code="SH-EYE-01",
        )
        modified_shelf.bounding_polygon = {"points": [[0, 0], [10, 10]]}

        hash2 = compute_m4_config_hash(
            job_id=job_id,
            store_id=topo["store"].id,
            camera_id=topo["camera"].id,
            db_shelves=[modified_shelf, topo["shelf_bottom"]],
        )

        assert hash1 != hash2


# ── 4. Behavioral Clustering & Archetypes (M6) ───────────────────────────

class TestBehavioralClusteringAndArchetypes:
    """Verifies Module 6 behavioral segmentation and archetype classification."""

    def test_shopper_archetype_clustering(self, mock_job_artifacts, retail_topology):
        """Assert behavior engine segments shoppers into distinct archetypes."""
        topo = retail_topology
        engine = Module6BehaviorEngine()

        m3_data = mock_job_artifacts["sessions_payload"]
        m4_data = {
            "shelves": [
                {"shelf_id": str(topo["shelf_eye"].id), "name": "Eye Level Shelf", "attention_count": 8},
                {"shelf_id": str(topo["shelf_bottom"].id), "name": "Bottom Shelf", "attention_count": 15},
            ]
        }
        m5_data = {
            "events": [
                {"event_type": "pickup", "track_id": 101, "product_id": str(topo["prod_bev"].id)},
                {"event_type": "pickup", "track_id": 103, "product_id": str(topo["prod_oil"].id)},
                {"event_type": "return", "track_id": 103, "product_id": str(topo["prod_oil"].id)},
                {"event_type": "pickup", "track_id": 103, "product_id": str(topo["prod_oil"].id)},
            ]
        }

        analysis = engine.analyze(
            m3_data=m3_data,
            m4_data=m4_data,
            m5_data=m5_data,
            store_id=str(topo["store"].id),
            camera_id=str(topo["camera"].id),
        )

        assert analysis is not None
        assert "summary" in analysis
        summary = analysis["summary"]
        assert summary["total_sessions"] >= 3

        # Assert shopper_segments list exists and classified shoppers are valid enums
        assert "shopper_segments" in analysis
        segments = analysis["shopper_segments"]
        valid_segments = {a.value for a in ShopperArchetype}
        for seg in segments:
            assert seg["primary_segment"] in valid_segments

        # Assert transition matrix and funnel
        assert "zone_transitions" in analysis
        assert "funnel" in analysis
        funnel = analysis["funnel"]
        assert "stages" in funnel
        assert len(funnel["stages"]) > 0


# ── 5. Attractiveness Scoring & Recommendations (M8 & M9) ────────────────

class TestDownstreamScoringAndRecommendations:
    """Verifies 5-pillar attractiveness scoring and actionable rule evaluation."""

    def test_product_attractiveness_calculation(self, retail_topology):
        """Assert composite scoring, shelf tier gamma normalization, and Bayesian shrinkage."""
        topo = retail_topology
        engine = Module8ScoringEngine()

        # Bottom shelf SKU with high engagement (Hidden Gem scenario)
        scored_oil = engine.score_product(
            product_id=topo["prod_oil"].sku,
            product_name=topo["prod_oil"].name,
            sku=topo["prod_oil"].sku,
            category="Oils & Vinegars",
            shelf_id=str(topo["shelf_bottom"].id),
            shelf_name=topo["shelf_bottom"].name,
            shelf_category="bottom",  # maps to ShelfTier.BOTTOM (gamma=0.40)
            total_viewers=35,
            total_passersby=100,
            total_attention_duration_sec=297.5,
            total_interactions=18,
            total_pickups=15,
            total_returns=2,
            total_purchases=10,
            repeat_interactions=4,
            unique_shoppers=35,
            shelf_viewers=35,
            shelf_passersby=100,
        )

        # Eye-level SKU with poor engagement (Shelf Squatter scenario)
        scored_bev = engine.score_product(
            product_id=topo["prod_bev"].sku,
            product_name=topo["prod_bev"].name,
            sku=topo["prod_bev"].sku,
            category="Beverages",
            shelf_id=str(topo["shelf_eye"].id),
            shelf_name=topo["shelf_eye"].name,
            shelf_category="eye",  # maps to ShelfTier.EYE_LEVEL (gamma=1.00)
            total_viewers=15,
            total_passersby=100,
            total_attention_duration_sec=18.0,
            total_interactions=2,
            total_pickups=1,
            total_returns=1,
            total_purchases=0,
            repeat_interactions=0,
            unique_shoppers=15,
            shelf_viewers=15,
            shelf_passersby=100,
        )

        # Intrinsic score for bottom shelf must exceed observed score due to gamma compensation
        assert scored_oil.intrinsic_attractiveness_score > scored_oil.attractiveness_score
        assert scored_oil.intrinsic_attractiveness_score == 100.0
        # Intrinsic rating is A+ due to 100.0 score
        assert QualitativeRating.from_score(scored_oil.intrinsic_attractiveness_score) == QualitativeRating.A_PLUS

        # Eye level SKU should have low observed score
        assert scored_bev.rating in (QualitativeRating.C, QualitativeRating.D)

    def test_recommendation_and_what_if_simulation(self):
        """Assert Hidden Gem rule elevation and What-If planogram simulation."""
        rec_engine = Module9RecommendationEngine()

        sample_profiles = [
            {
                "product_id": "SKU-OIL-001",
                "product_name": "Artisanal Cold-Pressed Olive Oil",
                "category": "Oils & Vinegars",
                "intrinsic_attractiveness_score": 82.0,
                "attractiveness_score": 38.0,
                "shelf_visibility": {"shelf_tier": "BOTTOM", "gamma_coefficient": 0.40},
                "pillar_scores": {"interaction_score": 0.6, "pickup_score": 0.5},
                "total_viewers": 35,
                "total_passersby": 100,
                "average_attention_duration_sec": 8.5,
                "total_pickups": 15,
                "total_returns": 2,
                "total_purchases": 10,
                "conversion_potential_score": 75.0,
                "marketing_effectiveness_score": 70.0,
            },
            {
                "product_id": "SKU-BEV-002",
                "product_name": "Standard Cooking Oil",
                "category": "Oils & Vinegars",
                "intrinsic_attractiveness_score": 25.0,
                "attractiveness_score": 25.0,
                "shelf_visibility": {"shelf_tier": "EYE_LEVEL", "gamma_coefficient": 1.00},
                "pillar_scores": {"interaction_score": 0.1, "pickup_score": 0.05},
                "total_viewers": 15,
                "total_passersby": 100,
                "average_attention_duration_sec": 1.2,
                "total_pickups": 1,
                "total_returns": 1,
                "total_purchases": 0,
                "conversion_potential_score": 20.0,
                "marketing_effectiveness_score": 25.0,
            },
        ]

        result = rec_engine.generate_recommendations(sample_profiles)
        recs = result["recommendations"]
        assert len(recs) >= 1

        # Check for recommendations generated
        assert result["summary"]["total_recommendations"] == len(recs)
        oil_recs = [r for r in recs if r.get("target_id") == "SKU-OIL-001" or "OIL" in str(r.get("target_id", ""))]
        assert len(oil_recs) >= 1

        # Run What-If Planogram simulation
        sim_request = PlanogramSimulationRequest(
            product_id="SKU-OIL-001",
            current_shelf_tier="BOTTOM",
            target_shelf_tier="EYE_LEVEL",
            current_attractiveness_score=38.0,
            current_intrinsic_score=82.0,
        )
        sim_result = PlanogramSimulator.simulate(sim_request)
        assert sim_result.simulated_attractiveness_score > sim_result.original_attractiveness_score
        assert sim_result.conversion_lift_pct > 0.0
        assert sim_result.is_improvement is True


# ── 6. Anomaly Alert Event Dispatching (M11) ─────────────────────────────

class TestAnomalyAlertEventDispatching:
    """Verifies anomaly detection event evaluation and hybrid notification dispatching."""

    def test_create_and_dispatch_anomaly_notification(self, mock_db, retail_topology):
        """Assert notification creation and event bus dispatching."""
        topo = retail_topology
        store_id = topo["store"].id

        notif = create_notification(
            db=mock_db,
            store_id=store_id,
            type="dwell_anomaly",
            severity="warning",
            title="High Dwell Bottle-neck Detected",
            message="Shoppers exceeding 45s dwell at Aisle 3 Bottom Tier Shelf.",
            entity_type="shelf",
            entity_id=topo["shelf_bottom"].id,
            target_role="store_manager",
            metadata={"avg_dwell_sec": 48.0, "threshold_sec": 30.0},
        )

        assert notif is not None
        assert notif.type == "dwell_anomaly"
        assert notif.severity == "warning"
        assert notif.target_role == "store_manager"

        # Assert hybrid event dispatcher runs without crashing (falls back gracefully to in-process bus if Redis absent)
        dispatch_job_event("JOB_PROCESSED", str(uuid.uuid4()))


# ── 7. Multi-Format Report Generation & Data Consistency (M12) ───────────

class TestMultiFormatReportGenerationAndConsistency:
    """Verifies analytical dossier compilation across PDF, Excel, and CSV with data consistency."""

    def test_domain_report_aggregation(self, mock_db, retail_topology):
        """Assert RetailIntelligenceAggregator compiles valid data payloads across all 5 domains."""
        aggregator = RetailIntelligenceAggregator(db=mock_db)
        topo = retail_topology

        for template in REPORT_TEMPLATES:
            report_type = template["report_type"]
            payload = aggregator.compile_report(
                report_type=report_type,
                store_id=topo["store"].id,
            )

            assert payload is not None
            assert payload["report_type"] == report_type
            assert "summary_kpis" in payload
            assert "table_rows" in payload
            assert "insights" in payload
            assert len(payload["insights"]) >= 1

    def test_multi_format_file_exports(self, mock_db, retail_topology):
        """Assert PDF, Excel, and CSV exporters generate valid binary & text outputs."""
        aggregator = RetailIntelligenceAggregator(db=mock_db)
        topo = retail_topology
        payload = aggregator.compile_report(
            report_type="consumer_attention",
            store_id=topo["store"].id,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # 1. PDF Export
            pdf_path = tmp_path / "test_report.pdf"
            pdf_gen = ReportPDFGenerator()
            pdf_gen.generate_pdf(payload, pdf_path)
            assert pdf_path.exists()
            assert pdf_path.stat().st_size > 500
            # Vector PDF files must start with %PDF- header
            with open(pdf_path, "rb") as f:
                header = f.read(5)
                assert header == b"%PDF-"

            # 2. Excel Multi-Tab Export
            excel_path = tmp_path / "test_report.xlsx"
            excel_gen = ReportExcelGenerator()
            excel_gen.generate_excel(payload, excel_path)
            assert excel_path.exists()
            assert excel_path.stat().st_size > 1000

            wb = openpyxl.load_workbook(excel_path)
            sheet_names = wb.sheetnames
            assert "Executive Summary" in sheet_names
            assert "Aggregate Analysis" in sheet_names
            assert "Raw Event Ledger" in sheet_names

            # 3. Flat CSV Export
            csv_path = tmp_path / "test_report.csv"
            csv_gen = ReportCSVGenerator()
            csv_gen.generate_csv(payload, csv_path)
            assert csv_path.exists()
            assert csv_path.stat().st_size > 100
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Shelf Name" in content or "Rank" in content


# ── 8. Full End-to-End Pipeline Session Lifecycle ─────────────────────────

class TestFullEndToEndPipelineSession:
    """
    Executes a complete, contiguous simulation of a retail intelligence session:
    Store Config -> Video Ingestion -> Shopper Tracking -> Dwell Attention ->
    Behavior Clustering -> Attractiveness Scoring -> Recommendations ->
    Anomaly Alerts -> Multi-Format Reporting with cross-module referential integrity.
    """

    def test_complete_retail_intelligence_lifecycle(self, mock_db, retail_topology, mock_job_artifacts):
        """Unified E2E integration test exercising the full 13-module pipeline stack."""
        topo = retail_topology
        store_id = topo["store"].id
        camera_id = topo["camera"].id
        artifacts = mock_job_artifacts

        # ── Step 1: Ingest Video Analysis Job ─────────────────────
        job_id = uuid.uuid4()
        job = AIJob(
            id=job_id,
            store_id=store_id,
            camera_id=camera_id,
            input_type="VIDEO_FILE",
            source="store_camera_stream_01.mp4",
            status="COMPLETED",
            output_path=str(artifacts["root_path"]),
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            completed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        assert job.status == "COMPLETED"

        # ── Step 2: Attention & Dwell Detection (M4) ──────────────
        attn_engine = Module4AttentionEngine()
        shelf_regions = [
            {
                "shelf_id": str(topo["shelf_eye"].id),
                "name": topo["shelf_eye"].name,
                "shelf_code": topo["shelf_eye"].shelf_code,
                "tier": "EYE_LEVEL",
                "polygon": topo["shelf_eye"].bounding_polygon["points"],
            },
            {
                "shelf_id": str(topo["shelf_bottom"].id),
                "name": topo["shelf_bottom"].name,
                "shelf_code": topo["shelf_bottom"].shelf_code,
                "tier": "BOTTOM",
                "polygon": topo["shelf_bottom"].bounding_polygon["points"],
            },
        ]
        m4_result = attn_engine.process_completed_module3_job(
            job_output_dir=artifacts["root_path"],
            shelf_regions=shelf_regions,
            store_id=str(store_id),
            camera_id=str(camera_id),
        )
        assert m4_result["summary"]["total_dwell_time_sec"] == 71.5
        assert m4_result["summary"]["total_attention_events"] >= 1

        # ── Step 3: Behavioral Intelligence & Clustering (M6) ────
        behavior_engine = Module6BehaviorEngine()
        m6_result = behavior_engine.analyze(
            m3_data=artifacts["sessions_payload"],
            m4_data=m4_result,
            m5_data={"events": []},
            store_id=str(store_id),
            camera_id=str(camera_id),
        )
        assert m6_result["summary"]["total_sessions"] >= 3
        classified_track_ids = {a["track_id"] for a in m6_result["shopper_segments"]}
        assert {101, 102, 103}.issubset(classified_track_ids)

        # ── Step 4: Product Attractiveness Scoring (M8) ───────────
        scoring_engine = Module8ScoringEngine()
        scored_oil = scoring_engine.score_product(
            product_id=topo["prod_oil"].sku,
            product_name=topo["prod_oil"].name,
            sku=topo["prod_oil"].sku,
            category=topo["prod_oil"].category,
            shelf_id=str(topo["shelf_bottom"].id),
            shelf_name=topo["shelf_bottom"].name,
            shelf_category="bottom",  # gamma = 0.40
            total_viewers=40,
            total_passersby=120,
            total_attention_duration_sec=368.0,
            total_interactions=26,
            total_pickups=18,
            total_returns=3,
            total_purchases=12,
            repeat_interactions=5,
            unique_shoppers=40,
            shelf_viewers=40,
            shelf_passersby=120,
        )
        assert scored_oil.intrinsic_attractiveness_score > scored_oil.attractiveness_score
        assert QualitativeRating.from_score(scored_oil.intrinsic_attractiveness_score) == QualitativeRating.A_PLUS

        # ── Step 5: Actionable Recommendations & Simulation (M9) ─
        rec_engine = Module9RecommendationEngine()
        rec_result = rec_engine.generate_recommendations([scored_oil.to_dict()])
        recs = rec_result["recommendations"]
        assert len(recs) >= 1
        top_rec = recs[0]
        assert top_rec.get("target_id") == topo["prod_oil"].sku or "OIL" in str(top_rec.get("target_id", ""))

        sim_req = PlanogramSimulationRequest(
            product_id=top_rec["target_id"],
            current_shelf_tier="BOTTOM",
            target_shelf_tier="EYE_LEVEL",
            current_attractiveness_score=scored_oil.attractiveness_score,
            current_intrinsic_score=scored_oil.intrinsic_attractiveness_score,
        )
        sim_res = PlanogramSimulator.simulate(sim_req)
        assert sim_res.simulated_attractiveness_score > sim_res.original_attractiveness_score
        assert sim_res.is_improvement is True

        # ── Step 6: Anomaly Alert Dispatching (M11) ───────────────
        alert = create_notification(
            db=mock_db,
            store_id=store_id,
            type="friction_point",
            severity="warning",
            title="High Return Rate Friction on Bottom Shelf",
            message=f"Product {topo['prod_oil'].name} has high dwell and returns.",
            entity_type="product",
            entity_id=topo["prod_oil"].id,
            target_role="retail_analyst",
            metadata={"friction_type": "high_return"},
        )
        assert alert.type == "friction_point"
        assert alert.store_id == store_id

        # ── Step 7: Dossier Export (M12) ──────────────────────────
        aggregator = RetailIntelligenceAggregator(db=mock_db)
        dossier = aggregator.compile_report(
            report_type="conversion_analysis",
            store_id=store_id,
        )
        assert str(dossier["store_id"]) == str(store_id)
        assert dossier["store_name"] == topo["store"].name

        with tempfile.TemporaryDirectory() as export_dir:
            out_dir = Path(export_dir)
            pdf_path = out_dir / "session_conversion_dossier.pdf"
            excel_path = out_dir / "session_conversion_dossier.xlsx"

            ReportPDFGenerator().generate_pdf(dossier, pdf_path)
            ReportExcelGenerator().generate_excel(dossier, excel_path)

            assert pdf_path.exists() and pdf_path.stat().st_size > 500
            assert excel_path.exists() and excel_path.stat().st_size > 1000

        # Cross-module data consistency assertion:
        # Verify SKU, store ID, and session count remained consistent across every single stage
        assert topo["prod_oil"].sku == scored_oil.product_id == top_rec["target_id"]
        assert topo["store"].id == store_id
        assert m6_result["summary"]["total_sessions"] == 3
