"""
Unit Tests — Batch Document Queries & Memory Fallback
======================================================
Tests high-performance batch retrieval for M4, M5, and M6 documents.
"""

import sys
from pathlib import Path
import uuid

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.repositories.ai_document_repository import AIDocumentRepository


def test_batch_module_analyses_memory_fallback():
    job1 = str(uuid.uuid4())
    job2 = str(uuid.uuid4())
    job3 = str(uuid.uuid4())

    # Seed mock analyses into repository memory store
    AIDocumentRepository.save_module4_analysis_sync(
        job_id=job1,
        analysis_data={"summary": {"total_attention_events": 15, "shelf_engagement_score_avg": 82.5}},
    )
    AIDocumentRepository.save_module4_analysis_sync(
        job_id=job2,
        analysis_data={"summary": {"total_attention_events": 25, "shelf_engagement_score_avg": 78.0}},
    )

    AIDocumentRepository.save_module5_analysis_sync(
        job_id=job1,
        analysis_data={"summary": {"total_pickups": 8}},
    )
    AIDocumentRepository.save_module5_analysis_sync(
        job_id=job2,
        analysis_data={"summary": {"total_pickups": 14}},
    )

    AIDocumentRepository.save_module6_analysis_sync(
        job_id=job1,
        analysis_data={"summary": {"segment_counts": {"EXPLORER": 3, "QUICK_BUYER": 2}}},
    )

    # Execute Batch Queries
    batch_m4 = AIDocumentRepository.get_batch_module4_analyses_sync([job1, job2, job3])
    assert len(batch_m4) == 2
    assert job1 in batch_m4
    assert batch_m4[job1]["summary"]["total_attention_events"] == 15
    assert batch_m4[job2]["summary"]["total_attention_events"] == 25
    assert job3 not in batch_m4

    batch_m5 = AIDocumentRepository.get_batch_module5_analyses_sync([job1, job2, job3])
    assert len(batch_m5) == 2
    assert batch_m5[job1]["summary"]["total_pickups"] == 8
    assert batch_m5[job2]["summary"]["total_pickups"] == 14

    batch_m6 = AIDocumentRepository.get_batch_module6_analyses_sync([job1, job2, job3])
    assert len(batch_m6) >= 1
    assert job1 in batch_m6
    assert batch_m6[job1]["summary"]["segment_counts"]["EXPLORER"] == 3
