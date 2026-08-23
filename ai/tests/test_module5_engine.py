"""
Unit and Integration Tests for Module 5 — Product Interaction Analysis Module
==============================================================================
Tests:
1. Product Viewed detection from Module 4 attention
2. Event deduplication across consecutive frames
3. Multi-person ByteTrack ID preservation & isolation
4. Product Pickup detection & insufficient visual evidence gating
5. Product Return detection & prior pickup validation
6. Multi-product comparison & consideration journey analysis
7. Shelf interaction monitoring (Visits vs Attention vs Interactions distinction)
8. Product engagement metric aggregation
9. Missing POS purchase data handling (no fake purchases)
10. Unconfigured product spatial mapping handling
11. Report generation (JSON and Markdown)
12. Completed job ingestion without re-running YOLO or ByteTrack
13. Database model persistence & API service layer
"""

import json
from pathlib import Path
import sys
import tempfile
import uuid
# pyrefly: ignore [missing-import]
import pytest

# Ensure backend and project root are in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# pyrefly: ignore [missing-import]
from app.modules.interaction.comparison_analyzer import Module5ComparisonAnalyzer
# pyrefly: ignore [missing-import]
from app.modules.interaction.engine import Module5InteractionEngine
# pyrefly: ignore [missing-import]
from app.modules.interaction.interaction_detector import Module5InteractionDetector
# pyrefly: ignore [missing-import]
from app.modules.interaction.models import (
    InteractionEventType,
    InteractionSource,
    Module5Summary,
    ProductComparisonPattern,
    ProductEngagementMetric,
    ProductInteractionEvent,
    ShelfInteractionMetric,
)
# pyrefly: ignore [missing-import]
from app.modules.interaction.pickup_return_detector import Module5PickupReturnDetector
# pyrefly: ignore [missing-import]
from app.modules.interaction.report_generator import Module5ReportGenerator
# pyrefly: ignore [missing-import]
from app.modules.interaction.shelf_interaction_monitor import Module5ShelfInteractionMonitor


# ── Test 1: Product Viewed Detection ─────────────────────────────────
def test_product_viewed_from_attention():
    """Verify PRODUCT_VIEWED events are correctly derived from Module 4 attention data."""
    detector = Module5InteractionDetector(dedup_gap_threshold_sec=1.0)

    attention_events = [
        {
            "event_id": "att_1",
            "track_id": 12,
            "session_id": "session_001",
            "target_type": "shelf",
            "target_id": "shelf_1",
            "target_name": "Beverage Shelf",
            "start_time": 5.0,
            "end_time": 7.5,
            "duration_seconds": 2.5,
            "confidence": 0.88,
            "attention_direction": "LEFT",
        }
    ]

    products_by_shelf = {
        "shelf_1": [
            {"id": "prod_101", "name": "Cola 500ml", "sku": "BEV-001", "shelf_id": "shelf_1"},
            {"id": "prod_102", "name": "Orange Juice", "sku": "BEV-002", "shelf_id": "shelf_1"},
        ]
    }
    products_by_id = {
        "prod_101": {"id": "prod_101", "name": "Cola 500ml", "sku": "BEV-001", "shelf_id": "shelf_1"},
        "prod_102": {"id": "prod_102", "name": "Orange Juice", "sku": "BEV-002", "shelf_id": "shelf_1"},
    }

    view_events = detector.extract_product_view_events(
        attention_events=attention_events,
        products_by_shelf=products_by_shelf,
        products_by_id=products_by_id,
        camera_id="cam_01",
        store_id="store_01",
    )

    assert len(view_events) == 2
    assert all(e.event_type == InteractionEventType.PRODUCT_VIEWED for e in view_events)
    assert all(e.track_id == 12 for e in view_events)
    assert all(e.duration_seconds == 2.5 for e in view_events)
    assert any(e.product_name == "Cola 500ml" for e in view_events)
    assert any(e.product_name == "Orange Juice" for e in view_events)


# ── Test 2: Event Deduplication Across Consecutive Frames ─────────────
def test_event_deduplication():
    """Verify that adjacent/overlapping view events for the same shopper & product are merged."""
    detector = Module5InteractionDetector(dedup_gap_threshold_sec=1.0)

    # Simulate 3 consecutive frame-level events for same shopper & product
    raw_events = [
        ProductInteractionEvent(
            event_id="e1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=5,
            session_id="session_01",
            product_id="prod_1",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=1.0,
            end_time=1.8,
            duration_seconds=0.8,
            confidence=0.85,
        ),
        ProductInteractionEvent(
            event_id="e2",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=5,
            session_id="session_01",
            product_id="prod_1",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=2.0,  # 0.2s gap (<= 1.0s threshold)
            end_time=3.5,
            duration_seconds=1.5,
            confidence=0.90,
        ),
        ProductInteractionEvent(
            event_id="e3",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=5,
            session_id="session_01",
            product_id="prod_1",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=10.0,  # 6.5s gap (> 1.0s threshold - distinct interaction)
            end_time=12.0,
            duration_seconds=2.0,
            confidence=0.88,
        ),
    ]

    deduped = detector.deduplicate_events(raw_events)

    # e1 and e2 should be merged into one continuous event [1.0 - 3.5], e3 remains separate
    assert len(deduped) == 2
    assert deduped[0].start_time == 1.0
    assert deduped[0].end_time == 3.5
    assert deduped[0].duration_seconds == 2.5
    assert deduped[1].start_time == 10.0
    assert deduped[1].duration_seconds == 2.0


# ── Test 3: Multi-Person ByteTrack ID Isolation ──────────────────────
def test_multi_person_tracking_isolation():
    """Verify that interactions from different ByteTrack IDs are never merged."""
    detector = Module5InteractionDetector(dedup_gap_threshold_sec=2.0)

    events = [
        ProductInteractionEvent(
            event_id="e1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=12,
            product_id="prod_1",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=5.0,
            end_time=7.0,
            duration_seconds=2.0,
        ),
        ProductInteractionEvent(
            event_id="e2",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=18,  # Different shopper viewing same product at same time
            product_id="prod_1",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=5.5,
            end_time=7.5,
            duration_seconds=2.0,
        ),
    ]

    deduped = detector.deduplicate_events(events)

    # Must preserve both separate shoppers
    assert len(deduped) == 2
    track_ids = {e.track_id for e in deduped}
    assert track_ids == {12, 18}


# ── Test 4: Product Pickup Detection & Gating ────────────────────────
def test_pickup_detection_insufficient_evidence_gating():
    """Verify pickup detection honestly reports insufficient evidence when fine hand tracking is absent."""
    detector = Module5PickupReturnDetector()

    view_events = [
        ProductInteractionEvent(
            event_id="v1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=10,
            session_id="s1",
            product_id="p1",
            product_name="Chips",
            shelf_id="shelf_2",
            start_time=2.0,
            end_time=6.0,
            duration_seconds=4.0,
        )
    ]

    events, pickup_status, purchase_status = detector.detect_pickups_and_returns(
        view_events=view_events,
        tracking_paths={},
        zone_visits=[],
        shelf_regions=[],
        pos_transactions=None,
        has_high_res_hand_tracking=False,  # Video CCTV evidence gating
    )

    # No fake pickup events should be generated
    assert len(events) == 0
    assert "INSUFFICIENT_VISUAL_EVIDENCE" in pickup_status
    assert "UNAVAILABLE / NOT CONFIGURED" in purchase_status


def test_pickup_detection_with_verified_evidence():
    """Verify pickup event is generated when verified evidence is supplied."""
    detector = Module5PickupReturnDetector(min_pickup_dwell_sec=2.0)

    view_events = [
        ProductInteractionEvent(
            event_id="v1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=10,
            session_id="s1",
            product_id="p1",
            product_name="Chips",
            shelf_id="shelf_2",
            start_time=2.0,
            end_time=6.0,
            duration_seconds=4.0,
            confidence=0.85,
        )
    ]

    events, pickup_status, purchase_status = detector.detect_pickups_and_returns(
        view_events=view_events,
        tracking_paths={},
        zone_visits=[],
        shelf_regions=[],
        has_high_res_hand_tracking=True,  # High-res tracking active
    )

    assert len(events) == 1
    assert events[0].event_type == InteractionEventType.PRODUCT_PICKED_UP
    assert events[0].track_id == 10
    assert events[0].product_name == "Chips"
    assert pickup_status == "VERIFIED_VISUAL_TRACKING"


# ── Test 5: Product Return Detection & Prior Pickup Requirement ───────
def test_return_detection_requires_prior_pickup():
    """Verify return events strictly require a prior verified pickup by the same shopper."""
    detector = Module5PickupReturnDetector(min_pickup_dwell_sec=1.5)

    view_events = [
        # First visit with pickup
        ProductInteractionEvent(
            event_id="v1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=7,
            session_id="session_7",
            product_id="p1",
            product_name="Soda",
            shelf_id="shelf_1",
            start_time=2.0,
            end_time=5.0,
            duration_seconds=3.0,
        ),
        # Later visit returning item to same shelf
        ProductInteractionEvent(
            event_id="v2",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=7,
            session_id="session_7",
            product_id="p1",
            product_name="Soda",
            shelf_id="shelf_1",
            start_time=12.0,
            end_time=14.0,
            duration_seconds=2.0,
        ),
    ]

    events, _, _ = detector.detect_pickups_and_returns(
        view_events=view_events,
        tracking_paths={},
        zone_visits=[],
        shelf_regions=[],
        has_high_res_hand_tracking=True,
    )

    # Should contain 1 PICKUP and 1 RETURN
    event_types = [e.event_type for e in events]
    assert InteractionEventType.PRODUCT_PICKED_UP in event_types
    assert InteractionEventType.PRODUCT_RETURNED in event_types

    return_ev = [e for e in events if e.event_type == InteractionEventType.PRODUCT_RETURNED][0]
    assert return_ev.track_id == 7
    assert return_ev.shelf_id == "shelf_1"
    assert return_ev.start_time == 12.0


# ── Test 6: Multi-Product Comparison & Consideration Analysis ─────────
def test_multi_product_comparison_analysis():
    """Verify observed multi-product consideration sequence extraction."""
    analyzer = Module5ComparisonAnalyzer()

    # Shopper 4 views Product A at t=2s, then Product B at t=6s, then Product A at t=10s
    events = [
        ProductInteractionEvent(
            event_id="e1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=4,
            session_id="session_004",
            product_id="pA",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=2.0,
            end_time=3.5,
            duration_seconds=1.5,
        ),
        ProductInteractionEvent(
            event_id="e2",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=4,
            session_id="session_004",
            product_id="pB",
            product_name="Product B",
            shelf_id="shelf_2",
            start_time=6.0,
            end_time=8.0,
            duration_seconds=2.0,
        ),
        ProductInteractionEvent(
            event_id="e3",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=4,
            session_id="session_004",
            product_id="pA",
            product_name="Product A",
            shelf_id="shelf_1",
            start_time=10.0,
            end_time=11.5,
            duration_seconds=1.5,
        ),
    ]

    patterns, comp_events = analyzer.analyze_comparisons(events)

    assert len(patterns) == 1
    assert len(comp_events) == 1

    pattern = patterns[0]
    assert pattern.track_id == 4
    assert pattern.session_id == "session_004"
    assert set(pattern.product_names) == {"Product A", "Product B"}
    assert len(pattern.interaction_sequence) == 3
    assert "Observed multi-product interaction" in pattern.pattern_description
    assert comp_events[0].event_type == InteractionEventType.PRODUCT_COMPARED


# ── Test 7: Shelf Interaction Monitoring Distinction ──────────────────
def test_shelf_interaction_monitoring_separation():
    """Verify distinct calculation of Shelf Visits vs Shelf Attention vs Shelf Interactions."""
    monitor = Module5ShelfInteractionMonitor()

    configured_shelves = [
        {"id": "shelf_1", "name": "Beverage Shelf", "shelf_code": "shelf_1", "zone_id": "zone_1"}
    ]

    zone_visits = [
        {"zone_id": "zone_1", "tracking_id": 1, "duration": 4.0},
        {"zone_id": "zone_1", "tracking_id": 2, "duration": 5.0},
        {"zone_id": "zone_1", "tracking_id": 3, "duration": 2.0},
    ]
    zone_dwell_map = {"zone_1": 11.0}
    zone_visitor_map = {"zone_1": 3}

    # Only 1 shopper paid sustained gaze attention to shelf_1
    events = [
        ProductInteractionEvent(
            event_id="ev_1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=2,
            product_id="p1",
            product_name="Water",
            shelf_id="shelf_1",
            start_time=1.0,
            end_time=3.5,
            duration_seconds=2.5,
        )
    ]

    metrics = monitor.compute_shelf_interactions(
        events=events,
        configured_shelves=configured_shelves,
        zone_visits=zone_visits,
        zone_dwell_map=zone_dwell_map,
        zone_visitor_map=zone_visitor_map,
        products_by_shelf={"shelf_1": [{"id": "p1", "name": "Water"}]},
    )

    assert len(metrics) == 1
    m = metrics[0]
    assert m.shelf_visits == 3          # 3 shoppers entered zone
    assert m.shelf_viewers == 1         # Only 1 shopper paid attention to shelf
    assert m.shelf_attention_duration_sec == 2.5
    assert m.shelf_interactions == 1    # Sustained interaction >= 1.0s


# ── Test 8: Product Engagement Metric Aggregation ─────────────────────
def test_product_engagement_metrics():
    """Verify product engagement calculation for views, duration, unique viewers, and repeats."""
    monitor = Module5ShelfInteractionMonitor()

    all_products = [
        {"id": "prod_1", "name": "Product 1", "sku": "SKU-1", "shelf_id": "shelf_1"}
    ]

    # Shopper 10 views twice, Shopper 20 views once
    events = [
        ProductInteractionEvent(
            event_id="e1",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=10,
            product_id="prod_1",
            product_name="Product 1",
            start_time=1.0,
            duration_seconds=2.0,
        ),
        ProductInteractionEvent(
            event_id="e2",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=10,
            product_id="prod_1",
            product_name="Product 1",
            start_time=5.0,
            duration_seconds=3.0,
        ),
        ProductInteractionEvent(
            event_id="e3",
            event_type=InteractionEventType.PRODUCT_VIEWED,
            track_id=20,
            product_id="prod_1",
            product_name="Product 1",
            start_time=8.0,
            duration_seconds=1.0,
        ),
    ]

    metrics = monitor.compute_product_engagement(
        events=events,
        all_products=all_products,
        comparison_events=[],
        is_spatial_mapped=False,
    )

    assert len(metrics) == 1
    p = metrics[0]
    assert p.views == 3
    assert p.unique_viewers == 2
    assert p.total_view_duration_sec == 6.0
    assert p.average_view_duration_sec == 2.0
    assert p.repeat_interactions == 1  # Shopper 10 had repeat interactions


# ── Test 9: Missing POS Data Handling ─────────────────────────────────
def test_missing_purchase_data_handling():
    """Verify POS purchase data absence is cleanly marked without fabricating purchase events."""
    detector = Module5PickupReturnDetector()
    events, _, purchase_status = detector.detect_pickups_and_returns(
        view_events=[],
        tracking_paths={},
        zone_visits=[],
        shelf_regions=[],
        pos_transactions=None,
    )

    assert len(events) == 0
    assert "UNAVAILABLE / NOT CONFIGURED" in purchase_status


# ── Test 10: Report Generation (JSON & Markdown) ──────────────────────
def test_report_generation_json_and_markdown():
    """Verify JSON and Markdown report rendering and writing."""
    generator = Module5ReportGenerator()

    summary = Module5Summary(
        total_views=5,
        total_unique_viewers=3,
        total_view_duration_sec=12.5,
        average_view_duration_sec=2.5,
        total_pickups=0,
        total_returns=0,
        total_comparisons=1,
        total_purchases=0,
        total_shelf_interactions=3,
        total_engagement_duration_sec=15.0,
    )

    products = [
        ProductEngagementMetric(
            product_id="p1",
            product_name="Energy Drink",
            sku="ENG-01",
            shelf_id="shelf_1",
            views=5,
            unique_viewers=3,
            total_view_duration_sec=12.5,
            average_view_duration_sec=2.5,
        )
    ]

    shelves = [
        ShelfInteractionMetric(
            shelf_id="shelf_1",
            shelf_name="Beverage Shelf",
            shelf_visits=10,
            shelf_viewers=3,
            shelf_attention_events=5,
            shelf_attention_duration_sec=12.5,
            product_views=5,
            shelf_interactions=3,
            total_engagement_duration_sec=12.5,
        )
    ]

    report_dict = generator.generate_json_report(
        summary=summary,
        products=products,
        shelves=shelves,
        events=[],
        comparisons=[],
    )

    assert report_dict["summary"]["total_views"] == 5
    assert len(report_dict["products"]) == 1
    assert len(report_dict["shelves"]) == 1

    md_text = generator.generate_markdown_report(report_dict)
    assert "# Module 5 — Product Interaction Analysis Report" in md_text
    assert "Energy Drink" in md_text
    assert "Beverage Shelf" in md_text

    with tempfile.TemporaryDirectory() as tmp_dir:
        json_p, md_p = generator.write_reports(report_dict, Path(tmp_dir))
        assert json_p.exists()
        assert md_p.exists()
        assert json_p.stat().st_size > 0
        assert md_p.stat().st_size > 0


# ── Test 11: End-to-End Completed Job Ingestion ───────────────────────
def test_process_completed_job_end_to_end():
    """Verify Module5InteractionEngine ingests completed job outputs from real artifacts."""
    engine = Module5InteractionEngine()

    sample_job_dir = _PROJECT_ROOT / "outputs" / "ai_jobs" / "dae2744d-1477-465f-a47a-b988d1f17312"
    if not sample_job_dir.exists():
        pytest.skip("Sample job directory does not exist")

    configured_shelves = [
        {"id": "shelf_1", "name": "Beverage Shelf", "shelf_code": "shelf_1", "zone_id": "zone_1"},
        {"id": "shelf_2", "name": "Snacks Shelf", "shelf_code": "shelf_2", "zone_id": "zone_2"},
        {"id": "shelf_3", "name": "Checkout Display", "shelf_code": "shelf_3", "zone_id": "zone_3"},
    ]

    configured_products = [
        {"id": "prod_1", "name": "Cola 500ml", "sku": "BEV-001", "shelf_id": "shelf_1"},
        {"id": "prod_2", "name": "Potato Chips", "sku": "SNK-001", "shelf_id": "shelf_2"},
        {"id": "prod_3", "name": "Gum Pack", "sku": "CHK-001", "shelf_id": "shelf_3"},
    ]

    report = engine.process_completed_job(
        job_output_dir=sample_job_dir,
        configured_shelves=configured_shelves,
        configured_products=configured_products,
        store_id="store_test",
        camera_id="cam_test",
    )

    assert report["module"] == "Module 5 — Product Interaction Analysis Module"
    assert "summary" in report
    assert "products" in report
    assert "shelves" in report
    assert len(report["shelves"]) == 3
    assert len(report["products"]) == 3
    assert (sample_job_dir / "module5" / "module5_interaction_report.json").exists()
    assert (sample_job_dir / "module5" / "module5_interaction_report.md").exists()


# ── Test 12: Database Models & Pydantic Schema Validation ─────────────
def test_database_models_and_schemas():
    """Verify document repository persistence and Pydantic schemas for Module 5."""
    # pyrefly: ignore [missing-import]
    from app.repositories.ai_document_repository import AIDocumentRepository
    # pyrefly: ignore [missing-import]
    from app.schemas.interaction import (
        InteractionEventItem,
        Module5AnalysisResponse,
        Module5SummarySchema,
        ProductComparisonItem,
        ProductEngagementItem,
        ShelfInteractionItem,
    )

    test_job_id = uuid.uuid4()
    test_cam_id = uuid.uuid4()
    test_store_id = uuid.uuid4()

    analysis_doc = {
        "job_id": str(test_job_id),
        "camera_id": str(test_cam_id),
        "store_id": str(test_store_id),
        "summary": {
            "total_views": 10,
            "total_pickups": 0,
            "total_returns": 0,
            "total_comparisons": 2,
            "total_purchases": 0,
            "total_unique_viewers": 5,
            "total_engagement_duration_sec": 25.0,
            "pickup_detection_status": "INSUFFICIENT_VISUAL_EVIDENCE",
            "purchase_data_status": "UNAVAILABLE / NOT CONFIGURED (No POS Data)",
        },
    }

    AIDocumentRepository.save_module5_analysis_sync(test_job_id, analysis_doc)
    loaded = AIDocumentRepository.get_module5_analysis_sync(str(test_job_id))
    assert loaded is not None
    assert loaded["summary"]["total_views"] == 10

    # Validate Pydantic response schema
    summary_schema = Module5SummarySchema(
        total_views=10,
        total_unique_viewers=5,
        total_view_duration_sec=25.0,
        average_view_duration_sec=2.5,
    )
    response_schema = Module5AnalysisResponse(
        job_id=test_job_id,
        camera_id=test_cam_id,
        store_id=test_store_id,
        status="COMPLETED",
        summary=summary_schema,
        products=[
            ProductEngagementItem(
                product_id="p1",
                product_name="Orange Juice",
                views=10,
                unique_viewers=5,
                total_view_duration_sec=25.0,
                average_view_duration_sec=2.5,
            )
        ],
        shelves=[
            ShelfInteractionItem(
                shelf_id="s1",
                shelf_name="Beverage Shelf",
                shelf_visits=15,
                shelf_viewers=5,
                shelf_attention_events=10,
                shelf_attention_duration_sec=25.0,
            )
        ],
        comparisons=[
            ProductComparisonItem(
                pattern_id="CMP_01",
                track_id=12,
                product_names=["Orange Juice", "Apple Juice"],
                total_duration_sec=10.0,
                start_time=2.0,
                end_time=12.0,
                pattern_description="Observed multi-product interaction",
            )
        ],
    )

    assert response_schema.job_id == test_job_id
    assert len(response_schema.products) == 1
    assert len(response_schema.shelves) == 1
    assert len(response_schema.comparisons) == 1

