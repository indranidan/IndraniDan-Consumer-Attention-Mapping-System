"""
Unit Tests for Module 3 and Module 4 Report Services
=====================================================
Validates:
- AIJobResultsResponse with Phase 6 report and markdown_report loading
- Module 3 structured report generation (get_job_report)
- Module 4 on-the-fly markdown synthesis (get_module4_report)
- Fallback summary extraction when job.summary in DB is empty
"""

import json
from pathlib import Path
import sys
import tempfile
import uuid
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker

# Ensure paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# pyrefly: ignore [missing-import]
from app.database.database import Base
# pyrefly: ignore [missing-import]
from app.models.ai_job import AIJob
# pyrefly: ignore [missing-import]
from app.repositories.ai_document_repository import AIDocumentRepository
# pyrefly: ignore [missing-import]
from app.services.ai_job_service import get_job_results, get_job_report
# pyrefly: ignore [missing-import]
from app.services.attention_service import get_module4_report


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_module3_results_and_report_loading(in_memory_db, tmp_path):
    # Create mock job output directory structure
    job_id = uuid.uuid4()
    job_output_dir = tmp_path / "ai_jobs" / str(job_id)
    p6_dir = job_output_dir / "phase6" / "reports"
    p6_dir.mkdir(parents=True, exist_ok=True)

    report_json_content = {
        "summary": {
            "total_unique_shoppers": 10,
            "total_sessions": 10,
            "completed_sessions": 8,
            "total_zone_visits": 15,
            "average_session_duration_sec": 12.5,
            "average_zone_dwell_time_sec": 4.2,
            "total_attention_events": 5,
            "total_estimated_attention_duration_sec": 7.8,
            "number_of_attention_targets": 2,
        },
        "shoppers": [
            {
                "tracking_id": 1,
                "session_id": "session_001",
                "session_status": "completed",
                "session_duration_sec": 12.5,
                "total_zone_dwell_time_sec": 4.2,
                "attention_event_count": 2,
                "total_estimated_attention_duration_sec": 3.5,
                "most_attended_target": "Snacks Shelf",
            }
        ],
        "zones": [
            {
                "zone_id": "zone_1",
                "zone_name": "Snacks Area",
                "total_visits": 10,
                "unique_shoppers": 8,
                "total_dwell_time_sec": 42.0,
                "average_dwell_time_sec": 4.2,
            }
        ],
        "targets": [
            {
                "target_id": "shelf_1",
                "target_name": "Snacks Shelf",
                "total_attention_sec": 7.8,
                "average_attention_sec": 1.56,
                "unique_viewers": 5,
                "total_events": 5,
            }
        ],
    }
    with open(p6_dir / "attention_report.json", "w", encoding="utf-8") as f:
        json.dump(report_json_content, f)

    report_md_content = "# Consumer Attention Analysis Report\n\n## 1. Executive Summary\n\nTotal unique shoppers: 10"
    with open(p6_dir / "attention_report.md", "w", encoding="utf-8") as f:
        f.write(report_md_content)

    job = AIJob(
        id=job_id,
        camera_id=uuid.uuid4(),
        store_id=uuid.uuid4(),
        input_type="VIDEO_FILE",
        source="test.mp4",
        status="COMPLETED",
        output_path=str(job_output_dir),
        created_by=uuid.uuid4(),
    )
    in_memory_db.add(job)
    in_memory_db.commit()

    # Test get_job_results
    results = get_job_results(in_memory_db, job_id)
    assert results.status == "COMPLETED"
    assert results.summary is not None
    assert results.summary["unique_shoppers"] == 10
    assert results.reports is not None
    assert results.reports["summary"]["total_unique_shoppers"] == 10
    assert results.markdown_report == report_md_content

    # Test get_job_report
    report_resp = get_job_report(in_memory_db, job_id)
    assert report_resp.job_id == job_id
    assert report_resp.json_report["summary"]["total_unique_shoppers"] == 10
    assert report_resp.markdown_report == report_md_content


def test_module4_on_the_fly_report_synthesis(in_memory_db, tmp_path):
    job_id = uuid.uuid4()
    job_output_dir = tmp_path / "ai_jobs" / str(job_id)
    job_output_dir.mkdir(parents=True, exist_ok=True)

    job = AIJob(
        id=job_id,
        camera_id=uuid.uuid4(),
        store_id=uuid.uuid4(),
        input_type="VIDEO_FILE",
        source="test.mp4",
        status="COMPLETED",
        output_path=str(job_output_dir),
        created_by=uuid.uuid4(),
    )
    in_memory_db.add(job)
    in_memory_db.commit()

    # Save analysis in AIDocumentRepository
    analysis_dict = {
        "job_id": str(job_id),
        "total_events": 3,
        "total_attention_duration_sec": 9.5,
        "average_attention_duration_sec": 3.17,
        "shelf_engagement_score_avg": 78.5,
        "shelves": [
            {
                "shelf_id": "shelf_1",
                "shelf_name": "Bakery",
                "visitors": 5,
                "viewers": 4,
                "dwell_time_sec": 20.0,
                "shelf_attention_time_sec": 9.5,
                "average_shelf_attention_sec": 2.37,
                "score": 78.5,
                "repeated_attention_events": 1,
            }
        ],
        "products": [],
        "quality_metrics": {
            "total_frames_analyzed": 100,
            "valid_face_detections": 80,
            "low_confidence_faces": 20,
            "face_detection_rate": 0.8,
            "average_pose_confidence": 0.85,
        },
        "summary": {
            "total_attention_events": 3,
            "total_attention_duration_sec": 9.5,
            "average_attention_duration_sec": 3.17,
            "total_dwell_time_sec": 20.0,
            "total_shelf_attention_time_sec": 9.5,
            "total_repeated_attention_events": 1,
            "total_unique_viewers": 4,
            "shelf_engagement_score_avg": 78.5,
        },
    }
    AIDocumentRepository.save_module4_analysis_sync(job_id, analysis_dict)

    # Note: module4_attention_report.md is deliberately NOT on disk
    # get_module4_report should synthesize it dynamically
    m4_report = get_module4_report(in_memory_db, job_id)
    assert m4_report.job_id == job_id
    assert m4_report.markdown_report is not None
    assert len(m4_report.markdown_report) > 0
    assert "Bakery" in m4_report.markdown_report
    assert "Shelf Engagement Analysis" in m4_report.markdown_report
