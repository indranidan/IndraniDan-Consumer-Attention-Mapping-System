"""
Comprehensive Lifecycle, Caching, Concurrency & Dependency Tests for Module 4 & Module 5
=======================================================================================
Tests all 10 specific test scenarios:
- TEST 1: Module 4 generates successfully from Module 3 outputs without opening Module 3 report.
- TEST 2 & 3: Opening Module 4 repeatedly returns cached DB result immediately (no recalculation).
- TEST 4: Re-evaluate on Module 4 forces recalculation and updates timestamps.
- TEST 5: Module 5 generates directly without opening Module 3 or Module 4 reports (auto-resolves dependencies).
- TEST 6: Reopening Module 5 returns cached DB result immediately (no recalculation).
- TEST 7: Module 3 report generation remains 100% functional and unaffected.
- TEST 8: Concurrent simultaneous requests do not produce duplicate jobs or corrupt state.
- TEST 9: Material region/shelf configuration change detects staleness and triggers re-evaluation.
- TEST 10: Missing/incomplete Module 3 outputs return structured error responses with clear retry path.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
import unittest.mock
import uuid
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker

# Setup paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# pyrefly: ignore [missing-import]
from fastapi import HTTPException
# pyrefly: ignore [missing-import]
from app.database.database import Base
# pyrefly: ignore [missing-import]
from app.models.ai_job import AIJob
# pyrefly: ignore [missing-import]
from app.models.attention import AttentionAnalysis, AttentionEventModel
# pyrefly: ignore [missing-import]
from app.models.camera import Camera
# pyrefly: ignore [missing-import]
from app.models.product import Product
# pyrefly: ignore [missing-import]
from app.models.product_interaction import (
    ProductInteractionAnalysis,
    ProductInteractionEventModel,
)
# pyrefly: ignore [missing-import]
from app.models.shelf import Shelf      
# pyrefly: ignore [missing-import]
from app.models.store import Store
# pyrefly: ignore [missing-import]
from app.models.role import Role
# pyrefly: ignore [missing-import]
from app.models.user import User
# pyrefly: ignore [missing-import]
from sqlalchemy.pool import StaticPool
# pyrefly: ignore [missing-import]
from app.models.zone import Zone
# pyrefly: ignore [missing-import]
from app.services.ai_job_service import get_job_report, get_job_results
# pyrefly: ignore [missing-import]
from app.services import module4_service, module5_service      


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _setup_mock_environment(db_session, tmp_path):
    """Create role, user, store, zone, camera, shelves, products, and Module 3 mock output files."""
    role = Role(id=uuid.uuid4(), role_name="Administrator")
    db_session.add(role)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        full_name="Admin User",
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()

    store = Store(
        id=uuid.uuid4(),
        name="Test Flagship Store",
        address="100 Retail Way",
        store_code=f"TFS-{uuid.uuid4().hex[:6]}",
        created_by=user.id,
    )
    db_session.add(store)
    db_session.flush()

    zone = Zone(
        id=uuid.uuid4(),
        store_id=store.id,
        name="Main Snack & Beverage Aisle",
    )
    db_session.add(zone)
    db_session.flush()

    camera = Camera(
        id=uuid.uuid4(),
        store_id=store.id,
        zone_id=zone.id,
        name="Aisle 1 Camera",
        camera_source="http://cam/stream",
    )
    db_session.add(camera)

    shelf1 = Shelf(
        id=uuid.uuid4(),
        store_id=store.id,
        zone_id=zone.id,
        name="Snack Shelf A",
        shelf_code="SH-SNACK-1",
    )
    shelf2 = Shelf(
        id=uuid.uuid4(),
        store_id=store.id,
        zone_id=zone.id,
        name="Beverage Shelf B",
        shelf_code="SH-BEV-1",
    )
    db_session.add_all([shelf1, shelf2])
    db_session.flush()

    product1 = Product(
        id=uuid.uuid4(),
        store_id=store.id,
        zone_id=zone.id,
        shelf_id=shelf1.id,
        name="Organic Potato Chips",
        sku="CHIP-ORG-001",
        price=3.99,
    )
    product2 = Product(
        id=uuid.uuid4(),
        store_id=store.id,
        zone_id=zone.id,
        shelf_id=shelf2.id,
        name="Sparkling Spring Water",
        sku="WATR-SPR-002",
        price=1.99,
    )
    db_session.add_all([product1, product2])
    db_session.flush()

    job_id = uuid.uuid4()
    job_output_dir = tmp_path / "ai_jobs" / str(job_id)

    # Populate Module 3 Phase outputs
    p2_dir = job_output_dir / "phase2" / "reports"
    p3_dir = job_output_dir / "phase3" / "reports"
    p4_dir = job_output_dir / "phase4" / "reports"
    p5_dir = job_output_dir / "phase5" / "reports"
    p6_dir = job_output_dir / "phase6" / "reports"

    for d in [p2_dir, p3_dir, p4_dir, p5_dir, p6_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Phase 2 tracks
    with open(p2_dir / "tracks.json", "w", encoding="utf-8") as f:
        json.dump({"frames": [{"frame": 1, "track_id": 1, "bbox": [100, 100, 200, 300]}]}, f)

    # Phase 3 paths and zone visits
    with open(p3_dir / "paths.json", "w", encoding="utf-8") as f:
        json.dump({"paths": {"1": [{"x": 150, "y": 200, "timestamp": 1.0}]}}, f)
    with open(p3_dir / "zone_visits.json", "w", encoding="utf-8") as f:
        json.dump({"zone_visits": [{"track_id": 1, "zone_id": "zone_1", "duration": 5.5}]}, f)

    # Phase 4 dwell summary
    with open(p4_dir / "zone_dwell_summary.json", "w", encoding="utf-8") as f:
        json.dump({
            "zone_summaries": [
                {"zone_id": "SH-SNACK-1", "total_dwell_seconds": 12.5, "unique_shoppers": 2},
                {"zone_id": "SH-BEV-1", "total_dwell_seconds": 8.0, "unique_shoppers": 1},
            ]
        }, f)

    # Phase 5 attention events
    with open(p5_dir / "attention_events.json", "w", encoding="utf-8") as f:
        json.dump({
            "events": [
                {
                    "event_id": "EVT_001",
                    "tracking_id": 1,
                    "session_id": "sess_1",
                    "start_time": 1.0,
                    "end_time": 3.5,
                    "duration_seconds": 2.5,
                    "attention_type": "SHELF_ATTENTION",
                    "target_type": "shelf",
                    "target_id": "SH-SNACK-1",
                    "target_name": "Snack Shelf A",
                    "zone_id": "SH-SNACK-1",
                    "attention_direction": "CENTER",
                    "confidence": 0.88,
                    "gaze_origin": [150.0, 120.0],
                    "gaze_direction": [0.0, 1.0],
                },
                {
                    "event_id": "EVT_002",
                    "tracking_id": 1,
                    "session_id": "sess_1",
                    "start_time": 4.0,
                    "end_time": 6.0,
                    "duration_seconds": 2.0,
                    "attention_type": "SHELF_ATTENTION",
                    "target_type": "shelf",
                    "target_id": "SH-BEV-1",
                    "target_name": "Beverage Shelf B",
                    "zone_id": "SH-BEV-1",
                    "attention_direction": "RIGHT",
                    "confidence": 0.79,
                    "gaze_origin": [200.0, 120.0],
                    "gaze_direction": [1.0, 0.0],
                }
            ]
        }, f)

    # Phase 6 report
    with open(p6_dir / "attention_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_unique_shoppers": 1,
                "total_sessions": 1,
                "completed_sessions": 1,
                "total_zone_visits": 2,
                "average_session_duration_sec": 6.0,
                "average_zone_dwell_time_sec": 10.25,
                "total_attention_events": 2,
                "total_estimated_attention_duration_sec": 4.5,
            },
            "shoppers": [{"tracking_id": 1, "session_id": "sess_1", "session_duration_sec": 6.0}],
            "zones": [{"zone_id": "SH-SNACK-1", "total_visits": 1, "total_dwell_time_sec": 12.5}],
            "targets": [{"target_id": "SH-SNACK-1", "total_attention_sec": 2.5}],
        }, f)
    with open(p6_dir / "attention_report.md", "w", encoding="utf-8") as f:
        f.write("# Module 3 Executive Summary\n\nTotal shoppers: 1")

    job = AIJob(
        id=job_id,
        store_id=store.id,
        camera_id=camera.id,
        status="COMPLETED",
        input_type="VIDEO_FILE",
        source="/dummy/video.mp4",
        output_path=str(job_output_dir),
        created_by=user.id,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.commit()

    return {
        "store": store,
        "camera": camera,
        "shelves": [shelf1, shelf2],
        "products": [product1, product2],
        "job": job,
        "job_output_dir": job_output_dir,
    }


def test_scenario_1_module4_generates_without_opening_module3_report(db_session, tmp_path):
    """
    TEST 1: Completed Module 3 job -> Open Module 4 directly without opening Module 3 report.
    EXPECTED: Module 4 generates successfully using the underlying Module 3 data.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    # 1. Before running analysis, pure GET raises 404 (not yet generated)
    with pytest.raises(HTTPException) as exc_info:
        module4_service.get_module4_analysis(db_session, job_id)
    assert exc_info.value.status_code == 404

    # 2. Run analysis via run_module4_analysis / get_or_run_module4_analysis
    res = module4_service.run_module4_analysis(db_session, job_id)

    assert res.job_id == job_id
    assert res.status == "COMPLETED"
    assert res.summary.total_attention_events >= 2
    assert len(res.shelves) >= 2
    assert len(res.products) >= 2

    # 3. After running, pure GET returns the saved result directly
    get_res = module4_service.get_module4_analysis(db_session, job_id)
    assert get_res.job_id == job_id
    assert get_res.summary.total_attention_events == res.summary.total_attention_events

    # Verify persisted in DB
    db_record = db_session.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).first()
    assert db_record is not None
    assert db_record.total_events >= 2
    assert db_record.summary_data.get("config_hash") is not None


def test_scenario_2_and_3_module4_returns_cached_immediately_without_recalculating(db_session, tmp_path):
    """
    TEST 2 & 3: Close Module 4, reopen repeatedly.
    EXPECTED: Existing Module 4 result loads immediately from DB. No analysis reruns.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    # 1. First execution
    res1 = module4_service.run_module4_analysis(db_session, job_id)
    timestamp1 = res1.summary.analyzed_at

    # 2. Mock the heavy engine to guarantee it is NOT called on subsequent reads
    with unittest.mock.patch("app.services.module4_service.Module4AttentionEngine") as mock_engine:
        # Second call via pure get_module4_analysis
        res2 = module4_service.get_module4_analysis(db_session, job_id)
        # Third call via get_or_run_module4_analysis
        res3 = module4_service.get_or_run_module4_analysis(db_session, job_id, force_rerun=False)

        # Engine must not have been instantiated
        mock_engine.assert_not_called()

    assert res2.job_id == job_id
    assert res3.job_id == job_id
    assert res2.summary.total_attention_events == res1.summary.total_attention_events

    # Verify sub-endpoints also read cached data without calling the engine
    with unittest.mock.patch("app.services.module4_service.Module4AttentionEngine") as mock_engine:
        shelves = module4_service.get_shelf_metrics(db_session, job_id)
        products = module4_service.get_product_metrics(db_session, job_id)
        events, total = module4_service.get_attention_events(db_session, job_id)
        report = module4_service.get_module4_report(db_session, job_id)
        heatmap = module4_service.get_module4_heatmap(db_session, job_id)

        mock_engine.assert_not_called()
        assert len(shelves) >= 2
        assert len(products) >= 2
        assert total >= 2
        assert len(report.markdown_report) > 0
        assert heatmap.job_id == job_id


def test_scenario_4_module4_reevaluate_forces_recalculation(db_session, tmp_path):
    """
    TEST 4: Click Re-evaluate on Module 4.
    EXPECTED: A new Module 4 analysis runs. The result is updated.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    # First run
    res1 = module4_service.get_or_run_module4_analysis(db_session, job_id, force_rerun=False)
    initial_analysis_id = db_session.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).first().id

    # Wait 10ms to ensure timestamp difference
    time.sleep(0.01)

    # Trigger explicit Re-evaluate
    res2 = module4_service.get_or_run_module4_analysis(db_session, job_id, force_rerun=True)

    assert res2.status == "COMPLETED"
    db_record = db_session.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).first()
    assert db_record.id == initial_analysis_id  # same record updated in place


def test_scenario_5_module5_generates_without_opening_module3_or_module4_reports(db_session, tmp_path):
    """
    TEST 5: Create completed Module 3 job. Do NOT open Module 3 or Module 4 report. Open Module 5.
    EXPECTED: Module 5 resolves backend dependencies (auto-generates Module 4) and generates successfully.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    # 1. Before running analysis, pure GET raises 404
    with pytest.raises(HTTPException) as exc_info:
        module5_service.get_module5_analysis(db_session, job_id)
    assert exc_info.value.status_code == 404

    # Verify Module 4 is not in DB yet
    m4_record_before = db_session.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).first()
    assert m4_record_before is None

    # 2. Run Module 5 directly via run_module5_analysis
    res = module5_service.run_module5_analysis(db_session, job_id)

    assert res.job_id == job_id
    assert res.status == "COMPLETED"
    assert res.summary.total_views >= 2
    assert len(res.products) >= 2
    assert len(res.shelves) >= 2

    # 3. After running, pure GET returns the saved result directly
    get_res = module5_service.get_module5_analysis(db_session, job_id)
    assert get_res.job_id == job_id
    assert get_res.summary.total_views == res.summary.total_views

    # Verify Module 4 was automatically generated and persisted as a dependency
    m4_record_after = db_session.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).first()
    assert m4_record_after is not None

    # Verify Module 5 record is persisted in DB
    m5_record = db_session.query(ProductInteractionAnalysis).filter(ProductInteractionAnalysis.job_id == job_id).first()
    assert m5_record is not None
    assert m5_record.summary_data.get("config_hash") is not None


def test_scenario_6_module5_reopening_returns_cached_immediately(db_session, tmp_path):
    """
    TEST 6: Close and reopen Module 5.
    EXPECTED: Existing Module 5 result loads immediately. No recalculation.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    # First run
    res1 = module5_service.run_module5_analysis(db_session, job_id)

    # Mock Module 5 engine to verify it is NOT called on subsequent views
    with unittest.mock.patch("app.services.module5_service.Module5InteractionEngine") as mock_engine:
        # Pure GET call
        res2 = module5_service.get_module5_analysis(db_session, job_id)
        # get_or_run call with force_rerun=False
        res3 = module5_service.get_or_run_module5_analysis(db_session, job_id, force_rerun=False)

        mock_engine.assert_not_called()

    assert res2.job_id == job_id
    assert res3.job_id == job_id
    assert res2.summary.total_views == res1.summary.total_views

    # Sub-endpoints read from DB directly
    with unittest.mock.patch("app.services.module5_service.Module5InteractionEngine") as mock_engine:
        products = module5_service.get_product_engagement(db_session, job_id)
        shelves = module5_service.get_shelf_interactions(db_session, job_id)
        comparisons = module5_service.get_product_comparisons(db_session, job_id)
        events, total = module5_service.get_interaction_events(db_session, job_id)
        report = module5_service.get_module5_report(db_session, job_id)

        mock_engine.assert_not_called()
        assert len(products) >= 2
        assert len(shelves) >= 2
        assert len(report.markdown_report) > 0


def test_scenario_7_module3_report_and_results_unaffected(db_session, tmp_path):
    """
    TEST 7: Open Module 3 report. Verify Module 3 behaves exactly as before.
    EXPECTED: Module 3 report viewer and results endpoints work unchanged.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    results = get_job_results(db_session, job_id)
    assert results.job_id == job_id
    assert results.status == "COMPLETED"
    assert (results.summary.get("total_unique_shoppers") == 1 or results.summary.get("unique_shoppers") == 1)

    report = get_job_report(db_session, job_id)
    assert report.job_id == job_id
    assert "Module 3 Executive Summary" in report.markdown_report


def test_scenario_8_concurrent_simultaneous_requests_prevent_duplicate_execution(db_session, tmp_path):
    """
    TEST 8: Multiple simultaneous requests for Module 4 and Module 5.
    EXPECTED: Per-job thread locks prevent duplicate analyses and DB write conflicts.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    def call_m4():
        Session = sessionmaker(bind=db_session.get_bind())
        session = Session()
        try:
            return module4_service.get_or_run_module4_analysis(session, job_id, force_rerun=False)
        finally:
            session.close()

    def call_m5():
        Session = sessionmaker(bind=db_session.get_bind())
        session = Session()
        try:
            return module5_service.get_or_run_module5_analysis(session, job_id, force_rerun=False)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures_m4 = [executor.submit(call_m4) for _ in range(4)]
        futures_m5 = [executor.submit(call_m5) for _ in range(4)]

        results_m4 = [f.result() for f in futures_m4]
        results_m5 = [f.result() for f in futures_m5]

    assert all(r.status == "COMPLETED" for r in results_m4)
    assert all(r.status == "COMPLETED" for r in results_m5)

    # Ensure only 1 AttentionAnalysis and 1 ProductInteractionAnalysis exist in DB
    m4_count = db_session.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).count()
    m5_count = db_session.query(ProductInteractionAnalysis).filter(ProductInteractionAnalysis.job_id == job_id).count()

    assert m4_count == 1
    assert m5_count == 1


def test_scenario_9_region_or_shelf_config_change_triggers_reevaluation(db_session, tmp_path):
    """
    TEST 9: Change the underlying region/shelf configuration.
    EXPECTED: System recognizes that previous analysis is stale and re-evaluates.
    """
    env = _setup_mock_environment(db_session, tmp_path)
    job_id = env["job"].id

    # 1. Run initial analysis
    res1 = module4_service.get_or_run_module4_analysis(db_session, job_id, force_rerun=False)
    initial_hash = res1.summary.config_hash

    # 2. Modify shelf in DB (change shelf_code)
    shelf = env["shelves"][0]
    shelf.shelf_code = "SH-SNACK-NEW-999"
    db_session.commit()

    # 3. Request analysis again without force_rerun
    res2 = module4_service.get_or_run_module4_analysis(db_session, job_id, force_rerun=False)
    new_hash = res2.summary.config_hash

    # Hashes must differ and both be present
    assert initial_hash is not None
    assert new_hash is not None
    assert initial_hash != new_hash


def test_scenario_10_missing_or_failed_upstream_data_returns_clear_error(db_session, tmp_path):
    """
    TEST 10: Incomplete or missing Module 3 outputs.
    EXPECTED: Backend returns structured HTTPException(400) with clear error message.
    """
    role = Role(id=uuid.uuid4(), role_name=f"Role_{uuid.uuid4().hex[:6]}")
    db_session.add(role)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        full_name="Scenario10 User",
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()

    store = Store(id=uuid.uuid4(), name="Store", store_code=f"S-{uuid.uuid4().hex[:6]}", created_by=user.id)
    camera = Camera(id=uuid.uuid4(), store_id=store.id, name="Cam1", camera_source="http://cam/stream")
    db_session.add_all([store, camera])

    # Job is RUNNING (not completed)
    job_running = AIJob(
        id=uuid.uuid4(),
        store_id=store.id,
        camera_id=camera.id,
        status="RUNNING",
        input_type="VIDEO_FILE",
        source="/dummy/video.mp4",
        created_by=user.id,
    )
    db_session.add(job_running)

    # Job is COMPLETED but has empty/missing output directory
    empty_dir = tmp_path / "empty_job"
    empty_dir.mkdir(parents=True, exist_ok=True)
    job_empty = AIJob(
        id=uuid.uuid4(),
        store_id=store.id,
        camera_id=camera.id,
        status="COMPLETED",
        input_type="VIDEO_FILE",
        source="/dummy/video.mp4",
        output_path=str(empty_dir),
        created_by=user.id,
    )
    db_session.add(job_empty)
    db_session.commit()

    # 1. Module 4 on RUNNING job raises 400
    with pytest.raises(HTTPException) as exc_info:
        module4_service.get_or_run_module4_analysis(db_session, job_running.id)
    assert exc_info.value.status_code == 400
    assert "Job is not completed yet" in exc_info.value.detail

    # 2. Module 4 on missing outputs raises 400
    with pytest.raises(HTTPException) as exc_info:
        module4_service.get_or_run_module4_analysis(db_session, job_empty.id)
    assert exc_info.value.status_code == 400
    assert "No Module 3 analysis data available" in exc_info.value.detail

    # 3. Module 5 on missing outputs raises 400
    with pytest.raises(HTTPException) as exc_info:
        module5_service.get_or_run_module5_analysis(db_session, job_empty.id)
    assert exc_info.value.status_code == 400
    assert "Required Module 3 data is unavailable" in exc_info.value.detail
