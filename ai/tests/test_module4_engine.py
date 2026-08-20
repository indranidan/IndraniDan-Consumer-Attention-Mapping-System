"""
Unit and Integration Tests for Module 4 — Attention Analysis Engine
=====================================================================
Tests:
- Head pose estimation and validation
- Gaze direction derivation (NO fake gaze)
- Low-confidence and occluded face handling
- Shelf engagement logic (presence in zone != shelf attention)
- Product attention (configured vs unconfigured placeholders)
- Attention event grouping & repeated attention event detection
- Metric duration calculations and scoring formula
- Multi-person ByteTrack ID preservation
- Completed Module 3 job ingestion without re-running YOLO or ByteTrack
- Report generation (JSON & Markdown)
- Camera heatmap generation
- Database model persistence
"""

from pathlib import Path
import sys
import tempfile
import uuid
import pytest
import numpy as np

# Ensure backend and project root are in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.module4.engine import Module4AttentionEngine

from app.module4.event_detector import Module4AttentionEventDetector
from app.module4.gaze_estimator import Module4GazeEstimator
from app.module4.head_pose import Module4HeadPoseEstimator
from app.module4.heatmap_generator import Module4HeatmapGenerator
from app.module4.metrics import (
    calculate_shelf_engagement_score,
    compute_product_metrics,
    compute_shelf_metrics,
)
from app.module4.models import (
    AttentionDirection,
    AttentionEventRecord,
    AttentionQualityMetrics,
    AttentionState,
    AttentionType,
    GazeEstimate,
    HeadPoseData,
    Module4Summary,
    ProductAttention,
    ShelfEngagement,
)
from app.module4.product_attention import Module4ProductAttentionDetector
from app.module4.report_generator import Module4ReportGenerator
from app.module4.shelf_engagement import Module4ShelfEngagementAnalyzer


# ── TEST 1: Completed Module 3 Ingestion without YOLO Rerun ───────
def test_module4_ingest_completed_job(tmp_path):
    """Test 1: Ingests existing job directory without executing YOLO or ByteTrack."""
    job_dir = tmp_path / "job_001"
    p4_dir = job_dir / "phase4" / "reports"
    p5_dir = job_dir / "phase5" / "reports"
    p4_dir.mkdir(parents=True)
    p5_dir.mkdir(parents=True)

    # Write dummy Phase 4 summary
    with open(p4_dir / "zone_dwell_summary.json", "w") as f:
        f.write('{"zones": [{"zone_id": "shelf_1", "total_dwell_seconds": 15.5, "unique_shoppers": 3}]}')

    # Write dummy Phase 5 events
    with open(p5_dir / "attention_events.json", "w") as f:
        f.write('''{
            "events": [
                {
                    "tracking_id": 10,
                    "target_type": "shelf",
                    "target_id": "shelf_1",
                    "target_name": "Beverage Shelf",
                    "start_time": 2.0,
                    "end_time": 5.5,
                    "duration_seconds": 3.5,
                    "attention_direction": "RIGHT",
                    "confidence": 0.85,
                    "visit_number": 1,
                    "gaze_origin": [250, 200],
                    "gaze_direction": [0.8, -0.2]
                }
            ]
        }''')

    engine = Module4AttentionEngine()
    shelves_config = [{"id": "shelf_1", "name": "Beverage Shelf", "type": "shelf", "polygon": [[100, 100], [500, 100], [500, 400], [100, 400]]}]

    res = engine.process_completed_module3_job(job_dir, shelf_regions=shelves_config)

    assert res["summary"]["total_attention_events"] == 1
    assert res["summary"]["total_shelf_attention_time_sec"] == 3.5
    assert len(res["shelves"]) == 1
    assert res["shelves"][0]["shelf_name"] == "Beverage Shelf"
    assert res["shelves"][0]["score"] > 0.0
    assert (job_dir / "module4" / "module4_attention_report.json").exists()
    assert (job_dir / "module4" / "module4_attention_report.md").exists()


# ── TEST 2: Head Pose Analysis ──────────────────────────────────
def test_head_pose_generation():
    """Test 2: HeadPoseData structure and properties."""
    pose = HeadPoseData(
        yaw=15.2,
        pitch=-8.1,
        roll=2.0,
        face_detected=True,
        confidence=0.88,
        face_bbox=(100, 50, 200, 180),
        nose_point=(150, 110),
        status="available",
        method="head_orientation",
    )
    assert pose.face_detected is True
    assert pose.yaw == 15.2
    assert pose.status == "available"
    assert pose.method == "head_orientation"


# ── TEST 3: Low Quality & Occluded Faces ─────────────────────────
def test_low_quality_occluded_faces():
    """Test 3: Small or occluded face crop returns unavailable safely."""
    estimator = Module4HeadPoseEstimator(min_detection_confidence=0.5)
    tiny_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    pose = estimator.estimate_from_crop(tiny_frame, (0, 0, 5, 5))
    assert pose.face_detected is False
    assert pose.status == "unavailable"


# ── TEST 4: Gaze Direction Calculation ──────────────────────────
def test_gaze_direction_calculation():
    """Test 4: Gaze calculation derives normalized direction vectors."""
    estimator = Module4GazeEstimator(yaw_threshold=15.0, pitch_threshold=15.0, confidence_threshold=0.5)

    # Looking right
    pose_right = HeadPoseData(yaw=30.0, pitch=0.0, face_detected=True, confidence=0.85, nose_point=(300, 200))
    gaze_r, dir_r, state_r = estimator.estimate_gaze(pose_right)
    assert dir_r == AttentionDirection.RIGHT
    assert state_r == AttentionState.ATTENDING
    assert gaze_r.is_valid is True
    assert gaze_r.direction[0] > 0 # dx positive for right
    assert gaze_r.method == "head_pose_based_attention"

    # Looking left
    pose_left = HeadPoseData(yaw=-30.0, pitch=0.0, face_detected=True, confidence=0.85, nose_point=(300, 200))
    gaze_l, dir_l, state_l = estimator.estimate_gaze(pose_left)
    assert dir_l == AttentionDirection.LEFT
    assert gaze_l.direction[0] < 0 # dx negative for left

    # Low confidence -> UNKNOWN
    pose_low = HeadPoseData(yaw=30.0, pitch=0.0, face_detected=True, confidence=0.2, nose_point=(300, 200))
    gaze_low, dir_low, state_low = estimator.estimate_gaze(pose_low)
    assert dir_low == AttentionDirection.UNKNOWN
    assert state_low == AttentionState.UNKNOWN
    assert gaze_low.is_valid is False


# ── TEST 5 & 6: Shelf Engagement & Zone Discrimination ────────────
def test_shelf_engagement_discrimination():
    """Test 5 & 6: Verify presence in zone != shelf attention."""
    analyzer = Module4ShelfEngagementAnalyzer(max_ray_distance=500)
    shelf_polygon = [[500, 100], [800, 100], [800, 400], [500, 400]]
    analyzer.register_region("shelf_1", "Snack Shelf", "shelf", shelf_polygon)

    # Case A: Shopper is at (300, 250) facing RIGHT toward shelf -> Engaged
    gaze_looking_at_shelf = GazeEstimate(
        origin=(300, 250),
        direction=(1.0, 0.0), # Rightward toward x=500
        confidence=0.9,
        is_valid=True,
    )
    hit_shelf = analyzer.find_engaged_shelf(gaze_looking_at_shelf, (300, 250))
    assert hit_shelf is not None
    assert hit_shelf.id == "shelf_1"

    # Case B: Shopper is at (300, 250) physically near shelf, but looking LEFT (facing away) -> NOT engaged
    gaze_facing_away = GazeEstimate(
        origin=(300, 250),
        direction=(-1.0, 0.0), # Leftward away from x=500
        confidence=0.9,
        is_valid=True,
    )
    miss_shelf = analyzer.find_engaged_shelf(gaze_facing_away, (300, 250))
    assert miss_shelf is None


# ── TEST 7 & 8: Event Grouping & Repeated Attention ──────────────
def test_attention_event_grouping_and_revisits():
    """Test 7 & 8: Consecutive frames grouped; look away creates separate events."""
    detector = Module4AttentionEventDetector(min_duration_sec=0.3)

    # Frame 1-3: looking at Beverage Shelf
    detector.update_track_attention(
        track_id=1, frame_number=1, timestamp=1.0,
        target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.9, zone_id="zone_1", state=AttentionState.ATTENDING,
    )
    detector.update_track_attention(
        track_id=1, frame_number=2, timestamp=1.5,
        target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.9, zone_id="zone_1", state=AttentionState.ATTENDING,
    )
    detector.update_track_attention(
        track_id=1, frame_number=3, timestamp=2.0,
        target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.9, zone_id="zone_1", state=AttentionState.ATTENDING,
    )

    # Frame 4: looks away -> UNKNOWN / NOT_ATTENDING
    detector.update_track_attention(
        track_id=1, frame_number=4, timestamp=2.5,
        target_id=None, target_name=None, target_type=None,
        direction=AttentionDirection.UNKNOWN, confidence=0.0, zone_id="zone_1", state=AttentionState.NOT_ATTENDING,
    )

    # Frame 5-6: looks back at Beverage Shelf again
    detector.update_track_attention(
        track_id=1, frame_number=5, timestamp=4.0,
        target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.9, zone_id="zone_1", state=AttentionState.ATTENDING,
    )
    detector.update_track_attention(
        track_id=1, frame_number=6, timestamp=4.8,
        target_id="shelf_1", target_name="Beverage Shelf", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.9, zone_id="zone_1", state=AttentionState.ATTENDING,
    )

    detector.close_all(frame_number=7, timestamp=5.0)
    events = detector.get_all_completed_events()

    assert len(events) == 2
    assert events[0].visit_number == 1
    assert events[0].duration_seconds == 1.5 # 1.0 to 2.5
    assert events[1].visit_number == 2
    assert events[1].duration_seconds == 1.0 # 4.0 to 5.0


# ── TEST 9: Shelf Attention Duration & Metrics ───────────────────
def test_shelf_metrics_calculation():
    """Test 9: Metrics separation and scoring formula."""
    events = [
        AttentionEventRecord(track_id=1, target_type="shelf", target_id="shelf_1", target_name="Shelf 1", duration_seconds=4.0, visit_number=1),
        AttentionEventRecord(track_id=1, target_type="shelf", target_id="shelf_1", target_name="Shelf 1", duration_seconds=2.0, visit_number=2),
    ]
    configured = [{"id": "shelf_1", "name": "Shelf 1", "type": "shelf"}]
    zone_dwell = {"shelf_1": 10.0}
    zone_visitors = {"shelf_1": 1}

    shelves = compute_shelf_metrics(events, configured, zone_dwell, zone_visitors)
    assert len(shelves) == 1
    s = shelves[0]
    assert s.shelf_attention_time_sec == 6.0
    assert s.dwell_time_sec == 10.0
    assert s.repeated_attention_events == 1
    assert s.viewers == 1
    assert s.score > 0.0

    # Test formula directly
    score = calculate_shelf_engagement_score(
        shelf_attention_time_sec=6.0,
        dwell_time_sec=10.0,
        repeated_events=1,
    )
    # 0.40*(6/10) + 0.35*(6/10) + 0.25*(1/3) = 0.24 + 0.21 + 0.0833 = 0.5333 * 100 = 53.3
    assert abs(score - 53.3) < 0.5


# ── TEST 10 & 11: Product Attention Handling ─────────────────────
def test_product_attention_handling():
    """Test 10 & 11: Product attention when configured vs unconfigured."""
    detector = Module4ProductAttentionDetector()

    # Case A: Not configured -> Returns placeholder without fabrication
    products_db = [{"id": "prod_1", "name": "Organic Milk", "sku": "MILK-01", "shelf_id": "shelf_1"}]
    unconfigured_list = detector.get_unconfigured_placeholder(products_db)
    assert len(unconfigured_list) == 1
    assert unconfigured_list[0].is_configured is False
    assert unconfigured_list[0].total_focus_duration_sec == 0.0
    assert "Unavailable / Not Configured" in unconfigured_list[0].status_note

    # Case B: Configured product polygon -> Detects intersection
    product_poly = [[200, 200], [300, 200], [300, 300], [200, 300]]
    detector.load_product_mappings([{
        "product_id": "prod_1",
        "name": "Organic Milk",
        "polygon": product_poly,
        "sku": "MILK-01",
        "shelf_id": "shelf_1",
    }])
    assert detector.is_configured is True

    gaze = GazeEstimate(origin=(100, 250), direction=(1.0, 0.0), is_valid=True, confidence=0.9)
    hit_prod = detector.find_focused_product(gaze)
    assert hit_prod is not None
    assert hit_prod.product_id == "prod_1"


# ── TEST 12: Multi-person ByteTrack ID Preservation ───────────────
def test_multiperson_track_preservation():
    """Test 12: Never merge events across distinct Track IDs."""
    detector = Module4AttentionEventDetector(min_duration_sec=0.3)

    # Shopper 17 looking at Shelf A
    detector.update_track_attention(
        track_id=17, frame_number=1, timestamp=1.0,
        target_id="shelf_A", target_name="Shelf A", target_type="shelf",
        direction=AttentionDirection.LEFT, confidence=0.85, zone_id="zone_1", state=AttentionState.ATTENDING,
    )
    # Shopper 21 looking at Shelf B
    detector.update_track_attention(
        track_id=21, frame_number=1, timestamp=1.0,
        target_id="shelf_B", target_name="Shelf B", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.88, zone_id="zone_2", state=AttentionState.ATTENDING,
    )

    detector.update_track_attention(
        track_id=17, frame_number=2, timestamp=2.0,
        target_id="shelf_A", target_name="Shelf A", target_type="shelf",
        direction=AttentionDirection.LEFT, confidence=0.85, zone_id="zone_1", state=AttentionState.ATTENDING,
    )
    detector.update_track_attention(
        track_id=21, frame_number=2, timestamp=2.5,
        target_id="shelf_B", target_name="Shelf B", target_type="shelf",
        direction=AttentionDirection.RIGHT, confidence=0.88, zone_id="zone_2", state=AttentionState.ATTENDING,
    )

    detector.close_all(frame_number=3, timestamp=3.0)
    events = detector.get_all_completed_events()

    events_17 = [e for e in events if e.track_id == 17]
    events_21 = [e for e in events if e.track_id == 21]

    assert len(events_17) == 1
    assert events_17[0].target_id == "shelf_A"
    assert len(events_21) == 1
    assert events_21[0].target_id == "shelf_B"


# ── TEST 13: Report Generation ──────────────────────────────────
def test_report_generation(tmp_path):
    """Test 13: JSON and Markdown attention report output."""
    generator = Module4ReportGenerator()

    summary = Module4Summary(
        total_attention_events=5,
        total_attention_duration_sec=12.5,
        average_attention_duration_sec=2.5,
        total_shelf_attention_time_sec=10.0,
        total_repeated_attention_events=2,
        total_unique_viewers=3,
        shelf_engagement_score_avg=65.4,
    )
    shelves = [
        ShelfEngagement(shelf_id="s1", shelf_name="Beverages", visitors=5, viewers=3, dwell_time_sec=15.0, shelf_attention_time_sec=10.0, average_shelf_attention_sec=2.5, score=65.4)
    ]
    products = [
        ProductAttention(product_id="p1", product_name="Soda", is_configured=False, status_note="Unavailable / Not Configured")
    ]
    events = [
        AttentionEventRecord(track_id=1, target_name="Beverages", start_time=1.0, end_time=3.5, duration_seconds=2.5)
    ]
    quality = AttentionQualityMetrics(
        total_frames_analyzed=100,
        valid_face_detections=80,
        face_detection_rate=0.8,
        average_pose_confidence=0.85,
    )

    report_json = generator.generate_json_report(summary, shelves, products, events, quality)
    assert report_json["summary"]["total_attention_events"] == 5
    assert "ESTIMATED" in report_json["disclaimer"]

    report_md = generator.generate_markdown_report(report_json)
    assert "# Module 4 — Consumer Attention Analysis Report" in report_md
    assert "Beverages" in report_md
    assert "Estimated Attention Analysis" in report_md

    j_path, m_path = generator.write_reports(report_json, tmp_path)
    assert j_path.exists()
    assert m_path.exists()


# ── TEST 14: Heatmap Generation ─────────────────────────────────
def test_heatmap_generation(tmp_path):
    """Test 14: 2D camera attention density map generation."""
    generator = Module4HeatmapGenerator(default_width=640, default_height=480)
    events = [
        AttentionEventRecord(
            track_id=1,
            gaze_origin=(200, 200),
            gaze_direction=(0.5, -0.5),
            duration_seconds=2.5,
            target_id="s1",
            target_name="Beverages",
        ),
        AttentionEventRecord(
            track_id=2,
            gaze_origin=(400, 300),
            gaze_direction=(-0.2, 0.8),
            duration_seconds=1.5,
            target_id="s2",
            target_name="Snacks",
        ),
    ]

    heatmap_data = generator.generate_heatmap_data(events, 640, 480)
    assert heatmap_data["total_points"] == 2
    assert len(heatmap_data["points"]) == 2

    img_path = tmp_path / "test_heatmap.png"
    rendered = generator.render_heatmap_image(events, img_path, 640, 480)
    assert rendered.exists()
    assert rendered.stat().st_size > 0
